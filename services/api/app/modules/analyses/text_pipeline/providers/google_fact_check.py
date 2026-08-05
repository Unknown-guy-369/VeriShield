from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
from app.modules.analyses.text_pipeline.schemas import SearchResult


class GoogleFactCheckProvider(EvidenceProvider):
    name = "google_fact_check"
    provider_hints = ("fact_check",)

    def __init__(self, api_key: str, *, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        if not self.api_key.strip():
            return ()
        return await asyncio.to_thread(self._search_sync, query, limit)

    def _search_sync(self, query: str, limit: int) -> tuple[SearchResult, ...]:
        params = {
            "query": query,
            "key": self.api_key,
            "pageSize": str(limit),
            "languageCode": "en",
        }
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        claims = payload.get("claims", [])
        results: list[SearchResult] = []
        for claim in claims[:limit]:
            review = self._best_review(claim)
            if review is None:
                continue
            publisher = review.get("publisher", {})
            url_value = review.get("url", "")
            if not url_value:
                continue
            results.append(
                SearchResult(
                    title=review.get("textualRating", "") or claim.get("text", "Fact-check result"),
                    url=url_value,
                    snippet=review.get("title", "") or claim.get("text", ""),
                    publisher=publisher.get("name"),
                    published_at=self._parse_date(review.get("reviewDate")),
                    relevance_hint=0.95,
                    provider_name=self.name,
                    fetchable=True,
                )
            )
        return tuple(results)

    def _best_review(self, claim: dict[str, Any]) -> dict[str, Any] | None:
        reviews = claim.get("claimReview", [])
        return reviews[0] if reviews else None

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
