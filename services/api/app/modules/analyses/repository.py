import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.analyses.models import AnalysisModel
from app.modules.analyses.schemas import (
    AnalysisRecord,
    AnalysisStatus,
    CreateAnalysisData,
)


class AnalysisRepository(ABC):
    @abstractmethod
    async def create(self, data: CreateAnalysisData) -> AnalysisRecord:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, analysis_id: UUID) -> AnalysisRecord | None:
        raise NotImplementedError


class MemoryAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self._records: dict[UUID, AnalysisRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, data: CreateAnalysisData) -> AnalysisRecord:
        now = datetime.now(UTC)
        record = AnalysisRecord(
            id=uuid4(),
            status=AnalysisStatus.QUEUED,
            progress=10,
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        async with self._lock:
            self._records[record.id] = record
        return record

    async def find_by_id(self, analysis_id: UUID) -> AnalysisRecord | None:
        async with self._lock:
            return self._records.get(analysis_id)


def model_to_record(model: AnalysisModel) -> AnalysisRecord:
    return AnalysisRecord(
        id=model.id,
        type=model.type,
        status=model.status,
        progress=model.progress,
        preferred_language=model.preferred_language,
        text=model.text,
        source_url=model.source_url,
        original_file_name=model.original_file_name,
        mime_type=model.mime_type,
        file_size=model.file_size,
        storage_path=model.storage_path,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyAnalysisRepository(AnalysisRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, data: CreateAnalysisData) -> AnalysisRecord:
        model = AnalysisModel(**data.model_dump())
        async with self._session_factory.begin() as session:
            session.add(model)
            await session.flush()
        return model_to_record(model)

    async def find_by_id(self, analysis_id: UUID) -> AnalysisRecord | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(AnalysisModel).where(AnalysisModel.id == analysis_id)
            )
        return model_to_record(model) if model else None
