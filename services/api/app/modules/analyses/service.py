import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
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
logger = logging.getLogger(__name__)


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
            record = await self.repository.create(
                CreateAnalysisData(
                    type=classified.type,
                    text=classified.text,
                    source_url=classified.source_url,
                    preferred_language=request.preferred_language,
                )
            )
            return record

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

    async def find_report(self, analysis_id: UUID) -> AnalysisRecord:
        return await self.find_one(analysis_id)

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

    async def process_analysis(self, analysis_id: UUID) -> None:
        from app.modules.analyses.schemas import AnalysisStatus
        from app.modules.analyses.text_pipeline.cross_examiner import LLMCrossExaminer
        from app.modules.analyses.text_pipeline.evidence_retriever import SecureHttpFetcher
        from app.modules.analyses.text_pipeline.pipeline import TextAnalysisPipeline
        from app.modules.analyses.text_pipeline.providers import (
            ExaSearchProvider,
            FixtureEvidenceProvider,
            GoogleFactCheckProvider,
            TavilySearchProvider,
        )
        from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
        record = await self.repository.find_by_id(analysis_id)
        if not record or record.type not in {AnalysisType.TEXT, AnalysisType.URL}:
            logger.warning(
                "analysis worker skipped id=%s reason=missing_record_or_non_text",
                analysis_id,
            )
            return

        progress = 15
        stage = "PREPROCESSING"
        logger.info("analysis stage id=%s stage=%s progress=%s", analysis_id, stage, progress)
        try:
            await self.repository.update(analysis_id, AnalysisStatus.PREPROCESSING, progress)
            text_to_analyze = record.text
            source_url = record.source_url
            fetcher = SecureHttpFetcher(timeout_seconds=self.settings.evidence_fetch_timeout_seconds)
            if record.type is AnalysisType.URL:
                if not source_url:
                    raise AppError(400, "URL_REQUIRED", "The URL analysis is missing its source URL.")
                fetched_title, _publisher, _published_at, fetched_text = await fetcher.fetch(source_url)
                text_to_analyze = fetched_text or fetched_title
                logger.info(
                    "analysis url extracted id=%s source_url=%s chars=%s",
                    analysis_id,
                    source_url,
                    len(text_to_analyze or ""),
                )
            if not text_to_analyze:
                raise AppError(400, "TEXT_REQUIRED", "There is no text available to analyze.")

            progress = 30
            stage = "FACT_CHECK"
            await self.repository.update(analysis_id, AnalysisStatus.ANALYZING, progress)
            providers: list[EvidenceProvider] = []
            if self.settings.google_fact_check_api_key:
                providers.append(
                    GoogleFactCheckProvider(
                        self.settings.google_fact_check_api_key,
                        timeout_seconds=self.settings.evidence_search_timeout_seconds,
                    )
                )
            tavily_key = self.settings.tavily_api_key or self.settings.search_api_key
            if tavily_key:
                providers.append(
                    TavilySearchProvider(
                        tavily_key,
                        timeout_seconds=self.settings.evidence_search_timeout_seconds,
                    )
                )
            if self.settings.exa_api_key:
                providers.append(
                    ExaSearchProvider(
                        self.settings.exa_api_key,
                        timeout_seconds=self.settings.evidence_search_timeout_seconds,
                    )
                )
            if self.settings.text_pipeline_fixture_fallback:
                providers.append(FixtureEvidenceProvider())
            logger.info(
                "analysis providers id=%s providers=%s",
                analysis_id,
                ",".join(provider.name for provider in providers) or "none",
            )

            progress = 45
            stage = "RETRIEVING"
            logger.info("analysis stage id=%s stage=%s progress=%s", analysis_id, stage, progress)
            await self.repository.update(analysis_id, AnalysisStatus.RETRIEVING, progress)

            cross_examiner = None
            if self.settings.llm_api_key and self.settings.llm_endpoint:
                cross_examiner = LLMCrossExaminer(
                    api_key=self.settings.llm_api_key,
                    endpoint=self.settings.llm_endpoint,
                    model=self.settings.llm_model,
                    timeout_seconds=self.settings.evidence_search_timeout_seconds,
                )
            pipeline = TextAnalysisPipeline.with_providers(
                providers=tuple(providers),
                fetcher=fetcher,
                cross_examiner=cross_examiner,
            )
            result = await pipeline.analyze(text_to_analyze, source_url=source_url)
            progress = 80
            stage = "SCORING"
            logger.info(
                "analysis stage id=%s stage=%s progress=%s claims=%s evidence=%s",
                analysis_id,
                stage,
                progress,
                len(result.claims),
                len(result.evidence),
            )
            await self.repository.update(analysis_id, AnalysisStatus.SCORING, progress)

            await self.repository.update(
                analysis_id,
                AnalysisStatus.COMPLETED,
                100,
                jsonable_encoder(result),
            )
            logger.info(
                "analysis completed id=%s stage=COMPLETED progress=100 claims=%s evidence=%s scores=%s",
                analysis_id,
                len(result.claims),
                len(result.evidence),
                len(result.scores),
            )
        except Exception:
            logger.exception(
                "analysis failed id=%s stage=%s progress=%s",
                analysis_id,
                stage,
                progress,
            )
            await self.repository.update(analysis_id, AnalysisStatus.FAILED, progress)
