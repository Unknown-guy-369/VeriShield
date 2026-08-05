from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class EvidenceStance(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"
    UNRELATED = "unrelated"


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    id: str
    index: int
    text: str
    normalized_text: str
    entities: tuple[str, ...] = ()
    source_url: str | None = None
    is_question: bool = False
    is_opinion: bool = False


@dataclass(frozen=True, slots=True)
class PlannedQuery:
    query: str
    provider_hints: tuple[str, ...] = ()
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class ClaimQueryPlan:
    claim_id: str
    queries: tuple[PlannedQuery, ...]


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    publisher: str | None = None
    published_at: datetime | None = None
    relevance_hint: float = 0.0
    provider_name: str = "unknown"
    fetchable: bool = True


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    id: str
    claim_id: str
    stance: EvidenceStance
    title: str
    publisher: str | None
    url: str
    published_at: datetime | None
    passage: str
    relevance: float
    source_reliability: int
    retrieval_confidence: float
    provider_name: str
    query: str
    canonical_url: str
    dedupe_key: str


@dataclass(frozen=True, slots=True)
class ClaimStanceResult:
    claim_id: str
    stance: EvidenceStance
    support_score: float
    contradict_score: float
    evidence_count: int
    reasoning: str


@dataclass(frozen=True, slots=True)
class CredibilityBreakdown:
    evidence_strength: float
    source_reliability: float
    source_diversity: float
    support_balance: float
    contradiction_penalty: float


@dataclass(frozen=True, slots=True)
class CredibilityScoreResult:
    claim_id: str
    score: int
    breakdown: CredibilityBreakdown
    formula: str
    reasoning: str


@dataclass(frozen=True, slots=True)
class TextAnalysisResult:
    claims: tuple[ClaimRecord, ...]
    claim_plans: tuple[ClaimQueryPlan, ...]
    evidence: tuple[EvidenceItem, ...]
    stances: tuple[ClaimStanceResult, ...]
    scores: tuple[CredibilityScoreResult, ...]


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    claim_id: str
    query: str
    results: tuple[SearchResult, ...] = field(default_factory=tuple)
