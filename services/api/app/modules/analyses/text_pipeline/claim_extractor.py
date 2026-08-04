from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.modules.analyses.text_pipeline.schemas import ClaimRecord

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
WHITESPACE_RE = re.compile(r"\s+")
QUOTED_TEXT_RE = re.compile(r"[\"“”']([^\"“”']{3,})[\"“”']")
CAPITALIZED_PHRASE_RE = re.compile(r"\b(?:[A-Z][\w&.-]*)(?:\s+[A-Z][\w&.-]*)+\b")
SINGLE_CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:\d+)?\b")
NUMBER_RE = re.compile(r"\b\d+(?:[.,:/-]\d+)*(?:%|km|kg|k|m|bn|crore|lakh|million|billion)?\b")
URL_RE = re.compile(r"https?://\S+")

OPINION_PREFIXES = (
    "i think",
    "i believe",
    "i feel",
    "in my opinion",
    "it seems",
    "it feels",
    "maybe",
    "perhaps",
    "probably",
    "likely",
    "should",
    "could",
    "would",
    "must",
)
QUESTION_PREFIXES = ("who ", "what ", "when ", "where ", "why ", "how ")
OPINION_MARKERS = (
    "opinion",
    "feel",
    "guess",
    "seems",
    "likely",
    "probably",
    "should",
    "could",
    "would",
)


@dataclass(frozen=True, slots=True)
class ClaimExtractor:
    source_url: str | None = None

    def extract(self, text: str) -> tuple[ClaimRecord, ...]:
        segments = self._split_segments(text)
        claims: list[ClaimRecord] = []
        for index, raw_segment in enumerate(segments):
            segment = self._clean_segment(raw_segment)
            if not segment:
                continue
            is_question = segment.endswith("?")
            if is_question:
                continue
            is_opinion = self._looks_like_opinion(segment)
            if is_opinion:
                continue
            normalized = self._normalize(segment)
            if not self._is_testable_fact(segment):
                continue
            entities = self._extract_entities(segment)
            claim_id = self._build_id(normalized, index)
            claims.append(
                ClaimRecord(
                    id=claim_id,
                    index=index,
                    text=segment,
                    normalized_text=normalized,
                    entities=entities,
                    source_url=self.source_url,
                    is_question=is_question,
                    is_opinion=is_opinion,
                )
            )
        return tuple(claims)

    def _split_segments(self, text: str) -> list[str]:
        cleaned = WHITESPACE_RE.sub(" ", text.strip())
        if not cleaned:
            return []
        parts = [part.strip(" \t\r\n-•*") for part in SENTENCE_SPLIT_RE.split(cleaned)]
        return [part for part in parts if part]

    def _clean_segment(self, segment: str) -> str:
        cleaned = segment.strip().strip("“”\"'")
        cleaned = cleaned.strip(" \t\r\n-•*")
        return cleaned

    def _normalize(self, segment: str) -> str:
        normalized = segment.lower()
        normalized = URL_RE.sub("<url>", normalized)
        normalized = normalized.rstrip(".!?;:")
        return WHITESPACE_RE.sub(" ", normalized).strip()

    def _looks_like_opinion(self, segment: str) -> bool:
        lowered = segment.lower().strip()
        if lowered.endswith("?"):
            return True
        return any(
            lowered.startswith(prefix) or f" {marker} " in f" {lowered} "
            for prefix in OPINION_PREFIXES
            for marker in OPINION_MARKERS
        )

    def _is_testable_fact(self, segment: str) -> bool:
        word_count = len(segment.split())
        if word_count < 4:
            return False
        if re.search(r"\b(is|was|were|has|have|reported|announced|said|showed|shows|confirmed|denied|released)\b", segment, re.I):
            return True
        if NUMBER_RE.search(segment) or CAPITALIZED_PHRASE_RE.search(segment):
            return True
        return bool(URL_RE.search(segment))

    def _extract_entities(self, segment: str) -> tuple[str, ...]:
        raw_entities: list[str] = []
        raw_entities.extend(QUOTED_TEXT_RE.findall(segment))
        raw_entities.extend(CAPITALIZED_PHRASE_RE.findall(segment))
        raw_entities.extend(SINGLE_CAPITALIZED_RE.findall(segment))
        raw_entities.extend(ACRONYM_RE.findall(segment))
        raw_entities.extend(NUMBER_RE.findall(segment))
        raw_entities.extend(URL_RE.findall(segment))
        return self._deduplicate(raw_entities)

    def _deduplicate(self, values: list[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            key = value.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(value.strip())
        return tuple(ordered)

    def _build_id(self, normalized: str, index: int) -> str:
        source = f"{normalized}|{self.source_url or ''}|{index}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
