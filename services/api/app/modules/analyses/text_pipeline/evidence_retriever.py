from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from html.parser import HTMLParser
from typing import Protocol, cast
from urllib.parse import SplitResult, parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
from app.modules.analyses.text_pipeline.schemas import (
    ClaimQueryPlan,
    EvidenceItem,
    EvidenceStance,
    SearchResult,
)

TRACKING_PARAM_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")
DEFAULT_TIMEOUT_SECONDS = 8.0
logger = logging.getLogger(__name__)


class TextPipelineError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class _ResponseLike(Protocol):
    headers: Message

    def read(self, amount: int = -1) -> bytes: ...

    def close(self) -> None: ...


class DocumentFetcher(Protocol):
    async def fetch(self, url: str) -> tuple[str, str | None, datetime | None, str]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class SecureHttpFetcher:
    user_agent: str = "VeriShield/1.0"
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_redirects: int = 3
    max_bytes: int = 512_000

    async def fetch(self, url: str) -> tuple[str, str | None, datetime | None, str]:
        return await asyncio.to_thread(self._fetch_sync, url)

    def _fetch_sync(self, url: str) -> tuple[str, str | None, datetime | None, str]:
        current_url = self._validate_public_http_url(url)
        opener = urllib.request.build_opener(_NoRedirectHandler())
        for _ in range(self.max_redirects + 1):
            request = urllib.request.Request(
                current_url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html, text/plain;q=0.9, */*;q=0.1",
                },
            )
            response, status, headers = self._open_request(opener, request)
            # pyrefly: ignore [missing-attribute]
            if 300 <= status < 400 and headers.get("Location"):
                current_url = self._validate_public_http_url(
                    urljoin(current_url, headers["Location"])
                )
                if response is not None:
                    response.close()
                continue

            if status >= 400:
                message = f"Evidence fetch failed with status {status}."
                if response is not None:
                    response.close()
                raise TextPipelineError(502, "EVIDENCE_FETCH_FAILED", message)

            if response is None:
                raise TextPipelineError(
                    502,
                    "EVIDENCE_FETCH_FAILED",
                    "The evidence response was empty.",
                )

            body = response.read(self.max_bytes + 1)[: self.max_bytes]
            try:
                encoding = headers.get_content_charset() or "utf-8"
            except AttributeError:
                encoding = "utf-8"
            content_type = headers.get("content-type", "").lower()
            if "text/html" in content_type or "application/xhtml+xml" in content_type:
                extractor = _HtmlDocumentExtractor()
                extractor.feed(body.decode(encoding, errors="ignore"))
                title = extractor.title or self._fallback_title(current_url)
                published_at = extractor.published_at
                publisher = extractor.publisher
                text = extractor.text
            else:
                title = self._fallback_title(current_url)
                published_at = None
                publisher = None
                text = body.decode(encoding, errors="ignore")
            response.close()
            return title, publisher, published_at, self._compact_text(text)

        raise TextPipelineError(
            504,
            "REDIRECT_LIMIT_EXCEEDED",
            "The evidence URL redirected too many times.",
        )

    def _open_request(
        self,
        opener: urllib.request.OpenerDirector,
        request: urllib.request.Request,
    ) -> tuple[_ResponseLike | None, int, Message]:
        try:
            response = cast(_ResponseLike, opener.open(request, timeout=self.timeout_seconds))
            status = getattr(response, "status", 200)
            return response, int(status), response.headers
        except urllib.error.HTTPError as error:
            return cast(_ResponseLike, error), int(error.code), error.headers

    def _validate_public_http_url(self, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"}:
            raise TextPipelineError(
                400,
                "INVALID_URL_SCHEME",
                "Only http and https URLs are allowed.",
            )
        if not parsed.hostname:
            raise TextPipelineError(400, "INVALID_URL", "The evidence URL is missing a host.")
        if parsed.username or parsed.password:
            raise TextPipelineError(400, "INVALID_URL", "Credentialed URLs are not allowed.")
        hostname = parsed.hostname.lower()
        if (
            hostname in {"localhost", "localhost.localdomain"}
            or hostname.endswith(".local")
            or hostname.endswith(".internal")
        ):
            raise TextPipelineError(
                400, "PRIVATE_URL_BLOCKED", "Local network URLs are not allowed."
            )
        if self._is_blocked_ip(hostname):
            raise TextPipelineError(
                400,
                "PRIVATE_URL_BLOCKED",
                "Private or loopback IP addresses are not allowed.",
            )
        try:
            infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror as error:
            raise TextPipelineError(
                400,
                "UNRESOLVABLE_HOST",
                "The evidence host could not be resolved.",
            ) from error
        addresses = {item[4][0] for item in infos if item[4]}
        if not addresses:
            raise TextPipelineError(
                400,
                "UNRESOLVABLE_HOST",
                "The evidence host could not be resolved.",
            )
        for address in addresses:
            # pyrefly: ignore [bad-argument-type]
            if self._is_blocked_ip(str(address)):
                raise TextPipelineError(
                    400,
                    "PRIVATE_URL_BLOCKED",
                    "Private or loopback IP addresses are not allowed.",
                )
        # pyrefly: ignore [bad-argument-type]
        return self._canonical_url(parsed)

    def _canonical_url(self, parsed: SplitResult) -> str:
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not any(key.lower().startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES)
        ]
        rebuilt = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            path=re.sub(r"/{2,}", "/", parsed.path or "/"),
            fragment="",
            query=urlencode(query, doseq=True),
        )
        return urlunsplit(rebuilt)

    def _fallback_title(self, url: str) -> str:
        return urlsplit(url).hostname or "evidence"

    def _compact_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _is_blocked_ip(self, value: str) -> bool:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return False
        return any(
            (
                address.is_private,
                address.is_loopback,
                address.is_link_local,
                address.is_multicast,
                address.is_reserved,
                address.is_unspecified,
            )
        )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):  # type: ignore[override]
        return None


class _HtmlDocumentExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.publisher: str | None = None
        self.published_at: datetime | None = None
        self._capture_title = False
        self._capture_text = True
        self._text_parts: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(part for part in self._text_parts if part).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "title":
            self._capture_title = True
        if tag.lower() in {"script", "style", "noscript"}:
            self._capture_text = False
        name = attrs_dict.get("name", "").lower()
        prop = attrs_dict.get("property", "").lower()
        content = attrs_dict.get("content", "")
        if name == "publisher" and content:
            self.publisher = content.strip()
        if prop in {"article:published_time", "og:published_time"} and content:
            self.published_at = self._parse_datetime(content)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._capture_title = False
        if tag.lower() in {"script", "style", "noscript"}:
            self._capture_text = True

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if not cleaned:
            return
        if self._capture_title and not self.title:
            self.title = cleaned
        if self._capture_text:
            self._text_parts.append(cleaned)

    def _parse_datetime(self, value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class EvidenceRetriever:
    providers: tuple[EvidenceProvider, ...]
    fetcher: DocumentFetcher
    max_results_per_claim: int = 6
    max_results_per_query: int = 3
    max_search_concurrency: int = 6
    max_fetch_concurrency: int = 8

    async def retrieve(self, plans: tuple[ClaimQueryPlan, ...]) -> tuple[EvidenceItem, ...]:
        evidence: list[EvidenceItem] = []
        seen: set[str] = set()
        search_semaphore = asyncio.Semaphore(self.max_search_concurrency)
        fetch_semaphore = asyncio.Semaphore(self.max_fetch_concurrency)

        for plan in plans:
            candidates = await self._search_plan(plan, search_semaphore)
            converted = await asyncio.gather(
                *(
                    self._convert_result(plan.claim_id, query, result, fetch_semaphore)
                    for query, result in candidates
                ),
                return_exceptions=True,
            )
            claim_count = 0
            for item in converted:
                if isinstance(item, BaseException):
                    logger.warning(
                        "evidence result skipped claim_id=%s error=%s",
                        plan.claim_id,
                        item,
                    )
                    continue
                if item is None or item.dedupe_key in seen:
                    continue
                seen.add(item.dedupe_key)
                evidence.append(item)
                claim_count += 1
                if claim_count >= self.max_results_per_claim:
                    break
        return tuple(evidence)

    async def _search_plan(
        self,
        plan: ClaimQueryPlan,
        semaphore: asyncio.Semaphore,
    ) -> tuple[tuple[str, SearchResult], ...]:
        requests: list[tuple[str, EvidenceProvider]] = []
        for planned_query in plan.queries:
            for provider in self.providers:
                provider_names = {provider.name, *provider.provider_hints}
                if planned_query.provider_hints and provider_names.isdisjoint(
                    planned_query.provider_hints
                ):
                    continue
                requests.append((planned_query.query, provider))

        results = await asyncio.gather(
            *(self._search_provider(query, provider, semaphore) for query, provider in requests),
            return_exceptions=True,
        )
        candidates: list[tuple[str, SearchResult]] = []
        for (query_text, provider), result in zip(requests, results, strict=True):
            if isinstance(result, BaseException):
                logger.warning(
                    "evidence provider failed provider=%s claim_id=%s query=%r error=%s",
                    provider.name,
                    plan.claim_id,
                    query_text,
                    result,
                )
                continue
            candidates.extend((query_text, item) for item in result)
        return tuple(candidates)

    async def _search_provider(
        self,
        query: str,
        provider: EvidenceProvider,
        semaphore: asyncio.Semaphore,
    ) -> tuple[SearchResult, ...]:
        async with semaphore:
            return await provider.search(query, limit=self.max_results_per_query)

    async def _convert_result(
        self,
        claim_id: str,
        query: str,
        result: SearchResult,
        fetch_semaphore: asyncio.Semaphore,
    ) -> EvidenceItem | None:
        canonical_url = self._canonical_dedupe_url(result.url)
        if canonical_url is None:
            return None
        published_at = result.published_at
        title = result.title
        publisher = result.publisher
        passage = result.snippet.strip()
        if result.fetchable:
            try:
                async with fetch_semaphore:
                    (
                        fetched_title,
                        fetched_publisher,
                        fetched_published_at,
                        fetched_passage,
                    ) = await self.fetcher.fetch(result.url)
                title = fetched_title or title
                publisher = fetched_publisher or publisher
                published_at = fetched_published_at or published_at
                passage = fetched_passage or passage
            except TextPipelineError:
                if not passage:
                    raise
        source_reliability = self._source_reliability(
            result.provider_name,
            result.publisher,
            result.url,
        )
        relevance = max(0.0, min(1.0, result.relevance_hint))
        retrieval_confidence = max(
            0.0,
            min(1.0, 0.55 + relevance * 0.35 + (source_reliability / 100) * 0.1),
        )
        dedupe_key = self._dedupe_key(canonical_url, title, publisher, passage)
        return EvidenceItem(
            id=hashlib.sha256(f"{claim_id}|{dedupe_key}".encode()).hexdigest()[:16],
            claim_id=claim_id,
            stance=EvidenceStance.INSUFFICIENT,
            title=title.strip() or result.title,
            publisher=publisher,
            url=result.url,
            published_at=published_at,
            passage=passage.strip(),
            relevance=relevance,
            source_reliability=source_reliability,
            retrieval_confidence=retrieval_confidence,
            provider_name=result.provider_name,
            query=query,
            canonical_url=canonical_url,
            dedupe_key=dedupe_key,
        )

    def _canonical_dedupe_url(self, url: str) -> str | None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        return urlunsplit(
            parsed._replace(
                scheme=parsed.scheme.lower(),
                netloc=parsed.netloc.lower(),
                fragment="",
                query="",
                path=re.sub(r"/{2,}", "/", parsed.path or "/"),
            )
        )

    def _dedupe_key(
        self,
        canonical_url: str,
        title: str,
        publisher: str | None,
        passage: str,
    ) -> str:
        normalized = "|".join(
            [
                canonical_url,
                title.strip().lower(),
                (publisher or "").strip().lower(),
                re.sub(r"\s+", " ", passage).lower()[:240],
            ]
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _source_reliability(self, provider_name: str, publisher: str | None, url: str) -> int:
        score = 45
        host = urlsplit(url).hostname or ""
        if provider_name == "google_fact_check":
            score += 35
        if provider_name == "fixture":
            score += 15
        if provider_name in {"tavily", "exa"}:
            score += 10
        if host.endswith(".gov") or host.endswith(".gov.in") or ".gov." in host:
            score += 20
        if host.endswith(".edu") or ".edu." in host:
            score += 10
        if publisher and any(
            token in publisher.lower()
            for token in ("government", "ministry", "commission", "department")
        ):
            score += 15
        return max(0, min(100, score))
