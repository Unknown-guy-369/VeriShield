from dataclasses import dataclass
from typing import cast

from fastapi import Request

from app.core.config import Settings
from app.database.session import Database
from app.modules.analyses.repository import (
    AnalysisRepository,
    MemoryAnalysisRepository,
    SqlAlchemyAnalysisRepository,
)
from app.modules.analyses.service import AnalysisService
from app.modules.media_forensics.image_analyzer import ImageAnalyzer
from app.modules.media_forensics.model_adapter import (
    BaseModelAdapter,
    MockModelAdapter,
    ONNXModelAdapter,
)
from app.modules.media_forensics.repository import MemoryMediaForensicsRepository
from app.modules.media_forensics.service import MediaForensicsService
from app.modules.media_forensics.video_analyzer import VideoAnalyzer
from app.storage.base import StorageAdapter
from app.storage.fallback import FallbackStorageAdapter
from app.storage.local import LocalStorageAdapter
from app.storage.supabase import SupabaseStorageAdapter


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    database: Database | None
    repository: AnalysisRepository
    storage: StorageAdapter
    analysis_service: AnalysisService
    media_forensics_service: MediaForensicsService

    @classmethod
    def build(cls, settings: Settings) -> "AppContainer":
        database_url = settings.database_url
        database = (
            Database(database_url.strip())
            if settings.database_configured and database_url is not None
            else None
        )
        repository: AnalysisRepository = (
            SqlAlchemyAnalysisRepository(database.session_factory)
            if database is not None
            else MemoryAnalysisRepository()
        )
        supabase_url = settings.supabase_url
        supabase_secret_key = settings.supabase_secret_key
        storage: StorageAdapter
        if (
            settings.supabase_storage_configured
            and supabase_url is not None
            and supabase_secret_key is not None
        ):
            storage = FallbackStorageAdapter(
                primary=SupabaseStorageAdapter(
                    supabase_url.strip(),
                    supabase_secret_key.strip(),
                    settings.supabase_storage_bucket,
                ),
                fallback=LocalStorageAdapter(settings.local_upload_dir),
            )
        else:
            storage = LocalStorageAdapter(settings.local_upload_dir)

        # Media Forensics Setup
        # For MVP, we default to MockModelAdapter if not configured, or if USE_LIVE_MODEL=False
        use_live_model = getattr(settings, "use_live_model", False)
        model_adapter: BaseModelAdapter
        if use_live_model:
            model_adapter = ONNXModelAdapter(getattr(settings, "onnx_model_path", "model.onnx"))
        else:
            model_adapter = MockModelAdapter()
            
        forensics_repository = MemoryMediaForensicsRepository()
        image_analyzer = ImageAnalyzer(model_adapter)
        video_analyzer = VideoAnalyzer(model_adapter)
        
        media_forensics_service = MediaForensicsService(
            analysis_repository=repository,
            forensics_repository=forensics_repository,
            storage=storage,
            image_analyzer=image_analyzer,
            video_analyzer=video_analyzer,
        )

        return cls(
            settings=settings,
            database=database,
            repository=repository,
            storage=storage,
            analysis_service=AnalysisService(repository, storage, settings),
            media_forensics_service=media_forensics_service,
        )

    async def close(self) -> None:
        if self.database is not None:
            await self.database.close()


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


def get_analysis_service(request: Request) -> AnalysisService:
    return get_container(request).analysis_service

def get_media_forensics_service(request: Request) -> MediaForensicsService:
    return get_container(request).media_forensics_service

