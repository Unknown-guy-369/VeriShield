from __future__ import annotations

from datetime import UTC, datetime

from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
from app.modules.analyses.text_pipeline.schemas import SearchResult


class FixtureEvidenceProvider(EvidenceProvider):
    name = "fixture"

    def __init__(self) -> None:
        now = datetime(2026, 8, 3, tzinfo=UTC)
        self._index = (
            {
                "title": "Government confirms free laptop rollout for eligible students",
                "url": "https://state.gov.in/education/free-laptops-announcement",
                "publisher": "Department of Education",
                "published_at": now,
                "snippet": "The department announced a phased laptop distribution program for eligible students.",
                "queries": {"free laptop", "education", "eligible students", "announced"},
            },
            {
                "title": "Fact check: no, the announcement is not a universal laptop giveaway",
                "url": "https://factcheck.example.org/universal-laptop-giveaway",
                "publisher": "Example Fact Check",
                "published_at": now,
                "snippet": "The claim overstates a targeted program and is therefore misleading.",
                "queries": {"free laptop", "misleading", "fact check", "giveaway"},
            },
            {
                "title": "Election commission clarifies result rumor",
                "url": "https://elections.example.gov/result-clarification",
                "publisher": "Election Commission",
                "published_at": now,
                "snippet": "Officials said the viral post misrepresented the tally and no official result had been announced.",
                "queries": {"result", "clarifies", "official result", "announced"},
            },
        )

    async def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        query_terms = {term for term in query.lower().split() if term}
        matches: list[SearchResult] = []
        for item in self._index:
            # pyrefly: ignore [not-iterable]
            haystack = " ".join((*item["queries"], item["title"], item["snippet"])).lower()
            overlap = len(query_terms.intersection(haystack.split()))
            if overlap == 0 and not any(term in haystack for term in query_terms):
                continue
            matches.append(
                SearchResult(
                    title=item["title"],
                    url=item["url"],
                    snippet=item["snippet"],
                    publisher=item["publisher"],
                    published_at=item["published_at"],
                    relevance_hint=min(1.0, 0.45 + overlap * 0.18),
                    provider_name=self.name,
                    fetchable=False,
                )
            )
        return tuple(matches[:limit])
