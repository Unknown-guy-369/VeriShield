import asyncio
from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.media_forensics.schemas import MediaAnalysisResult


class MediaForensicsRepository(ABC):
    @abstractmethod
    async def save_result(self, result: MediaAnalysisResult) -> MediaAnalysisResult:
        """Save a new media analysis result."""
        raise NotImplementedError

    @abstractmethod
    async def get_result(self, analysis_id: UUID) -> MediaAnalysisResult | None:
        """Retrieve a media analysis result by analysis ID."""
        raise NotImplementedError


class MemoryMediaForensicsRepository(MediaForensicsRepository):
    def __init__(self) -> None:
        self._results: dict[UUID, MediaAnalysisResult] = {}
        self._lock = asyncio.Lock()

    async def save_result(self, result: MediaAnalysisResult) -> MediaAnalysisResult:
        async with self._lock:
            self._results[result.analysis_id] = result
        return result

    async def get_result(self, analysis_id: UUID) -> MediaAnalysisResult | None:
        async with self._lock:
            return self._results.get(analysis_id)
