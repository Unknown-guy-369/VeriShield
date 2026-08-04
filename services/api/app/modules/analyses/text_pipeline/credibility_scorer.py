from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.modules.analyses.text_pipeline.schemas import (
    ClaimRecord,
    CredibilityBreakdown,
    CredibilityScoreResult,
    EvidenceItem,
    EvidenceStance,
)


@dataclass(frozen=True, slots=True)
class CredibilityScorer:
    def score(self, claim: ClaimRecord, evidence: tuple[EvidenceItem, ...]) -> CredibilityScoreResult:
        if not evidence:
            breakdown = CredibilityBreakdown(
                evidence_strength=0.0,
                source_reliability=0.0,
                source_diversity=0.0,
                support_balance=0.0,
                contradiction_penalty=0.0,
            )
            return CredibilityScoreResult(
                claim_id=claim.id,
                score=25,
                breakdown=breakdown,
                formula=self._formula(),
                reasoning="No evidence was available, so the claim remains weakly supported by default.",
            )

        support_weight = sum(self._weighted(item) for item in evidence if item.stance is EvidenceStance.SUPPORTED)
        contradict_weight = sum(self._weighted(item) for item in evidence if item.stance is EvidenceStance.CONTRADICTED)
        evidence_strength = min(1.0, len(evidence) / 6.0)
        source_reliability = sum(item.source_reliability for item in evidence) / (100 * len(evidence))
        source_diversity = min(1.0, len({item.publisher or item.url for item in evidence}) / 4.0)
        support_balance = support_weight - contradict_weight
        contradiction_penalty = min(1.0, contradict_weight + max(0.0, contradict_weight - support_weight))

        raw_score = (
            35.0
            + support_weight * 42.0
            + evidence_strength * 10.0
            + source_reliability * 8.0
            + source_diversity * 5.0
            - contradict_weight * 45.0
        )
        score = max(0, min(100, round(raw_score)))
        breakdown = CredibilityBreakdown(
            evidence_strength=round(evidence_strength, 4),
            source_reliability=round(source_reliability, 4),
            source_diversity=round(source_diversity, 4),
            support_balance=round(support_balance, 4),
            contradiction_penalty=round(contradiction_penalty, 4),
        )
        reasoning = self._build_reasoning(evidence)
        return CredibilityScoreResult(
            claim_id=claim.id,
            score=score,
            breakdown=breakdown,
            formula=self._formula(),
            reasoning=reasoning,
        )

    def _weighted(self, item: EvidenceItem) -> float:
        return item.relevance * item.retrieval_confidence * (item.source_reliability / 100)

    def _formula(self) -> str:
        return (
            "score = clamp(0,100, 35 + support_weight*42 + evidence_strength*10 "
            "+ source_reliability*8 + source_diversity*5 - contradict_weight*45)"
        )

    def _build_reasoning(self, evidence: tuple[EvidenceItem, ...]) -> str:
        counts = Counter(item.stance for item in evidence)
        return (
            f"Retrieved {len(evidence)} items: "
            f"{counts.get(EvidenceStance.SUPPORTED, 0)} supporting, "
            f"{counts.get(EvidenceStance.CONTRADICTED, 0)} contradicting, "
            f"{counts.get(EvidenceStance.INSUFFICIENT, 0)} insufficient, and "
            f"{counts.get(EvidenceStance.UNRELATED, 0)} unrelated."
        )
