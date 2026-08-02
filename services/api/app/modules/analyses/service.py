from pathlib import Path
from uuid import UUID

from starlette.datastructures import UploadFile

from app.core.config import Settings
from app.core.errors import AppError
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
        if request.type is AnalysisType.TEXT:
            self._reject_unexpected_file(upload)
            text = request.text or ""
            if len(text) > self.settings.text_max_length:
                raise AppError(400, "TEXT_TOO_LONG", "The submitted text is too long.")
            return await self.repository.create(
                CreateAnalysisData(
                    type=request.type,
                    text=text,
                    preferred_language=request.preferred_language,
                )
            )

        if request.type is AnalysisType.URL:
            self._reject_unexpected_file(upload)
            return await self.repository.create(
                CreateAnalysisData(
                    type=request.type,
                    source_url=str(request.source_url),
                    preferred_language=request.preferred_language,
                )
            )

        if upload is None:
            label = "image" if request.type is AnalysisType.IMAGE else "video"
            raise AppError(400, "FILE_REQUIRED", f"A {label} file is required.")

        size_limit = self._size_limit(request.type)
        content = await upload.read(size_limit + 1)
        if len(content) > size_limit:
            raise AppError(
                413,
                "UPLOAD_TOO_LARGE",
                f"The uploaded {request.type.value.lower()} exceeds the configured size limit.",
            )

        detected = detect_media_signature(content)
        self._validate_media_type(request.type, upload.content_type, detected.mime_type)

        stored: StoredObject | None = None
        try:
            stored = await self.storage.save(
                UploadPayload(
                    content=content,
                    extension=detected.extension,
                    mime_type=detected.mime_type,
                )
            )
            filename = Path(upload.filename or "upload").name[:255]
            return await self.repository.create(
                CreateAnalysisData(
                    type=request.type,
                    preferred_language=request.preferred_language,
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
    def _reject_unexpected_file(upload: UploadFile | None) -> None:
        if upload is not None:
            raise AppError(400, "UNEXPECTED_FILE", "Files are accepted only for IMAGE or VIDEO.")

    @staticmethod
    def _validate_media_type(
        analysis_type: AnalysisType,
        claimed_mime_type: str | None,
        detected_mime_type: str,
    ) -> None:
        allowed = IMAGE_MIME_TYPES if analysis_type is AnalysisType.IMAGE else VIDEO_MIME_TYPES
        if claimed_mime_type not in allowed or detected_mime_type not in allowed:
            raise AppError(
                400,
                "MEDIA_TYPE_MISMATCH",
                f"The uploaded file is not a supported {analysis_type.value.lower()} format.",
            )
