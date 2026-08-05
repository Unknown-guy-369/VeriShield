from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.modules.analyses.text_pipeline.schemas import ClaimQueryPlan, ClaimRecord, PlannedQuery

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "that",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True, slots=True)
class QueryPlanner:
    def plan(self, claims: tuple[ClaimRecord, ...]) -> tuple[ClaimQueryPlan, ...]:
        return tuple(ClaimQueryPlan(claim_id=claim.id, queries=self._plan_for_claim(claim)) for claim in claims)

    def _plan_for_claim(self, claim: ClaimRecord) -> tuple[PlannedQuery, ...]:
        search_phrases = self._search_phrases(claim)
        query_specs = [
            (search_phrases[0], ("fact_check", "official_web", "fixture"), "Start with the exact factual statement."),
            (f"{search_phrases[0]} fact check", ("fact_check", "fixture"), "Check for debunks, corrections, and verdict pages."),
            (f"{search_phrases[0]} official source", ("official_web", "fixture"), "Prefer authoritative primary sources."),
            (f"{search_phrases[1]} site:gov.in OR site:gov", ("official_web", "fixture"), "Bias toward government and public-institution sources."),
            (f"{search_phrases[1]} news report", ("news", "fixture"), "Look for corroborating reporting from reputable outlets."),
        ]
        queries: list[PlannedQuery] = []
        seen: set[str] = set()
        for query, hints, rationale in query_specs:
            normalized = self._normalize_query(query)
            if normalized in seen:
                continue
            seen.add(normalized)
            queries.append(
                PlannedQuery(
                    query=query.strip(),
                    provider_hints=hints,
                    rationale=rationale,
                )
            )
        return tuple(queries[:5])

    def _search_phrases(self, claim: ClaimRecord) -> tuple[str, str]:
        exact = self._trim_to_query(claim.text)
        entity_text = " ".join(claim.entities[:3]).strip()
        if not entity_text:
            entity_text = self._keywords(claim.normalized_text)
        return exact or claim.normalized_text, entity_text or exact or claim.normalized_text

    def _trim_to_query(self, text: str, limit: int = 16) -> str:
        words = text.split()
        if len(words) <= limit:
            return text
        return " ".join(words[:limit])

    def _keywords(self, normalized_text: str) -> str:
        tokens = [
            token
            for token in re.split(r"\W+", normalized_text.lower())
            if token and token not in STOPWORDS and len(token) > 2
        ]
        if not tokens:
            return normalized_text
        return " ".join(tokens[:6])

    def _normalize_query(self, query: str) -> str:
        compact = re.sub(r"\s+", " ", query.lower()).strip()
        return hashlib.sha1(compact.encode("utf-8")).hexdigest()
