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
        return cls(
            settings=settings,
            database=database,
            repository=repository,
            storage=storage,
            analysis_service=AnalysisService(repository, storage, settings),
        )

    async def close(self) -> None:
        if self.database is not None:
            await self.database.close()


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


def get_analysis_service(request: Request) -> AnalysisService:
    return get_container(request).analysis_service
