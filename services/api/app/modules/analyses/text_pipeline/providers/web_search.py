from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
from app.modules.analyses.text_pipeline.schemas import SearchResult

logger = logging.getLogger(__name__)


class TavilySearchProvider(EvidenceProvider):
    name = "tavily"
    provider_hints = ("news", "official_web", "web")

    def __init__(self, api_key: str, *, timeout_seconds: float = 8.0) -> None:
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        if not self.api_key:
            return ()
        return await asyncio.to_thread(self._search_sync, query, limit)

    def _search_sync(self, query: str, limit: int) -> tuple[SearchResult, ...]:
        body = json.dumps(
            {
                "api_key": self.api_key,
                "query": query,
                "max_results": limit,
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        payload = self._load_json(request)
        results = payload.get("results", [])
        parsed: list[SearchResult] = []
        for item in results[:limit]:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            parsed.append(
                SearchResult(
                    title=str(item.get("title") or "Search result").strip(),
                    url=url,
                    snippet=str(item.get("content") or item.get("snippet") or "").strip(),
                    publisher=None,
                    published_at=_parse_datetime(item.get("published_date")),
                    relevance_hint=_score_to_relevance(item.get("score")),
                    provider_name=self.name,
                    fetchable=True,
                )
            )
        return tuple(parsed)

    def _load_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as error:
            logger.warning("tavily search failed: %s", error)
            return {}


class ExaSearchProvider(EvidenceProvider):
    name = "exa"
    provider_hints = ("news", "official_web", "web")

    def __init__(self, api_key: str, *, timeout_seconds: float = 8.0) -> None:
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        if not self.api_key:
            return ()
        return await asyncio.to_thread(self._search_sync, query, limit)

    def _search_sync(self, query: str, limit: int) -> tuple[SearchResult, ...]:
        body = json.dumps(
            {
                "query": query,
                "numResults": limit,
                "type": "auto",
                "contents": {"text": {"maxCharacters": 1200}},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.exa.ai/search",
            data=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        payload = self._load_json(request)
        results = payload.get("results", [])
        parsed: list[SearchResult] = []
        for item in results[:limit]:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            parsed.append(
                SearchResult(
                    title=str(item.get("title") or "Search result").strip(),
                    url=url,
                    snippet=str(item.get("text") or item.get("summary") or "").strip(),
                    publisher=str(item.get("author") or "").strip() or None,
                    published_at=_parse_datetime(item.get("publishedDate")),
                    relevance_hint=_score_to_relevance(item.get("score")),
                    provider_name=self.name,
                    fetchable=True,
                )
            )
        return tuple(parsed)

    def _load_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as error:
            logger.warning("exa search failed: %s", error)
            return {}


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _score_to_relevance(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    return 0.7
