from pathlib import Path
from uuid import UUID, uuid4

from starlette.datastructures import UploadFile

from app.core.config import Settings
from app.core.errors import AppError
from app.modules.analyses.classifier import InputClassifier
from app.modules.analyses.media_signature import detect_media_signature
from app.modules.analyses.repository import AnalysisRepository
from app.modules.analyses.schemas import (
    AnalysisRecord,
    AnalysisType,
    CreateAnalysisData,
    CreateAnalysisRequest,
)
from app.storage.base import StorageAdapter, StoredObject, UploadPayload

IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


class AnalysisService:
    def __init__(
        self,
        repository: AnalysisRepository,
        storage: StorageAdapter,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.settings = settings

    async def create(
        self,
        request: CreateAnalysisRequest,
        upload: UploadFile | None = None,
    ) -> AnalysisRecord:
        input_text = request.input
        if input_text and len(input_text) > self.settings.text_max_length:
            raise AppError(400, "TEXT_TOO_LONG", "The submitted text is too long.")

        if upload is None:
            if input_text is None:
                raise AppError(
                    400,
                    "INPUT_REQUIRED",
                    "Enter a claim or URL, or attach an image or video.",
                )
            classified = InputClassifier.classify_text(input_text)
            if classified.type is AnalysisType.TEXT and len(input_text) < 10:
                raise AppError(
                    400,
                    "INPUT_TOO_SHORT",
                    "Enter at least 10 characters so there is enough context to analyze.",
                )
            return await self.repository.create(
                CreateAnalysisData(
                    type=classified.type,
                    text=classified.text,
                    source_url=classified.source_url,
                    preferred_language=request.preferred_language,
                )
            )

        content = await upload.read(self.settings.upload_max_mb * 1024 * 1024 + 1)
        if len(content) > self.settings.upload_max_mb * 1024 * 1024:
            raise AppError(
                413,
                "UPLOAD_TOO_LARGE",
                "The uploaded file exceeds the configured size limit.",
            )

        detected = detect_media_signature(content)
        classified = InputClassifier.classify_media(detected.mime_type, input_text)
        self._validate_media_type(classified.type, upload.content_type)
        size_limit = self._size_limit(classified.type)
        if len(content) > size_limit:
            raise AppError(
                413,
                "UPLOAD_TOO_LARGE",
                f"The uploaded {classified.type.value.lower()} exceeds the configured size limit.",
            )

        analysis_id = uuid4()
        stored: StoredObject | None = None
        try:
            stored = await self.storage.save(
                UploadPayload(
                    analysis_id=analysis_id,
                    content=content,
                    extension=detected.extension,
                    mime_type=detected.mime_type,
                )
            )
            filename = Path(upload.filename or "upload").name[:255]
            return await self.repository.create(
                CreateAnalysisData(
                    id=analysis_id,
                    type=classified.type,
                    preferred_language=request.preferred_language,
                    text=classified.text,
                    original_file_name=filename,
                    mime_type=detected.mime_type,
                    file_size=len(content),
                    storage_path=stored.storage_path,
                )
            )
        except Exception:
            if stored is not None:
                await self.storage.remove(stored)
            raise
        finally:
            await upload.close()

    async def find_one(self, analysis_id: UUID) -> AnalysisRecord:
        record = await self.repository.find_by_id(analysis_id)
        if record is None:
            raise AppError(404, "ANALYSIS_NOT_FOUND", "The requested analysis does not exist.")
        return record

    def _size_limit(self, analysis_type: AnalysisType) -> int:
        megabytes = (
            self.settings.image_max_mb
            if analysis_type is AnalysisType.IMAGE
            else self.settings.upload_max_mb
        )
        return megabytes * 1024 * 1024

    @staticmethod
    def _validate_media_type(
        analysis_type: AnalysisType,
        claimed_mime_type: str | None,
    ) -> None:
        allowed = IMAGE_MIME_TYPES if analysis_type is AnalysisType.IMAGE else VIDEO_MIME_TYPES
        if claimed_mime_type and claimed_mime_type not in allowed:
            raise AppError(
                400,
                "MEDIA_TYPE_MISMATCH",
                f"The uploaded file is not a supported {analysis_type.value.lower()} format.",
            )
