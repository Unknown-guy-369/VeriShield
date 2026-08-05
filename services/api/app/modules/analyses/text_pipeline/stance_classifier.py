from __future__ import annotations

import re
from dataclasses import dataclass, replace

from app.modules.analyses.text_pipeline.schemas import (
    ClaimRecord,
    ClaimStanceResult,
    EvidenceItem,
    EvidenceStance,
)

SUPPORT_CUES = {
    "announced",
    "confirmed",
    "reported",
    "says",
    "said",
    "shows",
    "showed",
    "states",
    "released",
    "official",
    "according",
    "verifies",
    "evidence",
}
CONTRADICT_CUES = {
    "false",
    "debunked",
    "hoax",
    "fabricated",
    "denied",
    "not true",
    "no evidence",
    "misleading",
    "incorrect",
    "untrue",
    "did not",
}
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
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True, slots=True)
class StanceClassifier:
    def classify(self, claim: ClaimRecord, evidence: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        classified = [self._classify_item(claim, item) for item in evidence]
        return tuple(classified)

    def summarize(self, claim: ClaimRecord, evidence: tuple[EvidenceItem, ...]) -> ClaimStanceResult:
        supported = 0.0
        contradicted = 0.0
        for item in evidence:
            weighted = item.relevance * (item.source_reliability / 100) * item.retrieval_confidence
            if item.stance is EvidenceStance.SUPPORTED:
                supported += weighted
            elif item.stance is EvidenceStance.CONTRADICTED:
                contradicted += weighted
        if not evidence:
            return ClaimStanceResult(
                claim_id=claim.id,
                stance=EvidenceStance.INSUFFICIENT,
                support_score=0.0,
                contradict_score=0.0,
                evidence_count=0,
                reasoning="No evidence was retrieved for the claim.",
            )
        if contradicted > supported * 1.1 and contradicted >= 0.25:
            stance = EvidenceStance.CONTRADICTED
            reasoning = "Contradicting evidence outweighs supporting evidence."
        elif supported > contradicted * 1.1 and supported >= 0.25:
            stance = EvidenceStance.SUPPORTED
            reasoning = "Supporting evidence outweighs contradicting evidence."
        elif supported == 0 and contradicted == 0:
            stance = EvidenceStance.UNRELATED
            reasoning = "Retrieved evidence was not clearly connected to the claim."
        else:
            stance = EvidenceStance.INSUFFICIENT
            reasoning = "The evidence mix is not strong enough to resolve the claim."
        return ClaimStanceResult(
            claim_id=claim.id,
            stance=stance,
            support_score=round(supported, 4),
            contradict_score=round(contradicted, 4),
            evidence_count=len(evidence),
            reasoning=reasoning,
        )

    def _classify_item(self, claim: ClaimRecord, item: EvidenceItem) -> EvidenceItem:
        claim_terms = self._claim_terms(claim.normalized_text)
        passage = item.passage.lower()
        overlap = len(claim_terms.intersection(self._claim_terms(passage)))
        support_hits = sum(1 for cue in SUPPORT_CUES if cue in passage)
        contradict_hits = sum(1 for cue in CONTRADICT_CUES if cue in passage)
        if overlap == 0:
            stance = EvidenceStance.UNRELATED
        elif contradict_hits > support_hits and contradict_hits >= 1:
            stance = EvidenceStance.CONTRADICTED
        elif support_hits > contradict_hits and support_hits >= 1:
            stance = EvidenceStance.SUPPORTED
        elif overlap >= 2 and support_hits == contradict_hits == 0:
            stance = EvidenceStance.SUPPORTED if item.relevance >= 0.55 else EvidenceStance.INSUFFICIENT
        else:
            stance = EvidenceStance.INSUFFICIENT
        return replace(item, stance=stance)

    def _claim_terms(self, text: str) -> set[str]:
        terms = {
            token
            for token in re.split(r"\W+", text.lower())
            if token and token not in STOPWORDS and len(token) > 2
        }
        return terms
