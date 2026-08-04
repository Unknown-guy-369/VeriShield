from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.analyses.text_pipeline.schemas import SearchResult


class EvidenceProvider(ABC):
    name: str = "provider"

    @abstractmethod
    async def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        raise NotImplementedError
