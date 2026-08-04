from __future__ import annotations

from dataclasses import dataclass

from app.modules.analyses.text_pipeline.claim_extractor import ClaimExtractor
from app.modules.analyses.text_pipeline.credibility_scorer import CredibilityScorer
from app.modules.analyses.text_pipeline.evidence_retriever import EvidenceRetriever, SecureHttpFetcher
from app.modules.analyses.text_pipeline.query_planner import QueryPlanner
from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
from app.modules.analyses.text_pipeline.schemas import TextAnalysisResult
from app.modules.analyses.text_pipeline.stance_classifier import StanceClassifier


@dataclass(frozen=True, slots=True)
class TextAnalysisPipeline:
    claim_extractor: ClaimExtractor
    query_planner: QueryPlanner
    retriever: EvidenceRetriever
    stance_classifier: StanceClassifier
    credibility_scorer: CredibilityScorer

    @classmethod
    def with_fixture_provider(cls, providers: tuple[EvidenceProvider, ...]) -> "TextAnalysisPipeline":
        fetcher = SecureHttpFetcher()
        retriever = EvidenceRetriever(providers=providers, fetcher=fetcher)
        return cls(
            claim_extractor=ClaimExtractor(),
            query_planner=QueryPlanner(),
            retriever=retriever,
            stance_classifier=StanceClassifier(),
            credibility_scorer=CredibilityScorer(),
        )

    async def analyze(self, text: str) -> TextAnalysisResult:
        claims = self.claim_extractor.extract(text)
        plans = self.query_planner.plan(claims)
        evidence = await self.retriever.retrieve(plans)
        stances = []
        scores = []
        for claim in claims:
            claim_evidence = tuple(item for item in evidence if item.claim_id == claim.id)
            classified = self.stance_classifier.classify(claim, claim_evidence)
            summary = self.stance_classifier.summarize(claim, classified)
            stances.append(summary)
            scores.append(self.credibility_scorer.score(claim, classified))
        return TextAnalysisResult(
            claims=claims,
            claim_plans=plans,
            evidence=evidence,
            stances=tuple(stances),
            scores=tuple(scores),
        )
