from __future__ import annotations

from dataclasses import dataclass

from app.modules.analyses.text_pipeline.claim_extractor import ClaimExtractor
from app.modules.analyses.text_pipeline.credibility_scorer import CredibilityScorer
from app.modules.analyses.text_pipeline.cross_examiner import LLMCrossExaminer
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
    cross_examiner: LLMCrossExaminer | None = None

    @classmethod
    def with_providers(
        cls,
        providers: tuple[EvidenceProvider, ...],
        *,
        fetcher: SecureHttpFetcher | None = None,
        cross_examiner: LLMCrossExaminer | None = None,
    ) -> "TextAnalysisPipeline":
        active_fetcher = fetcher or SecureHttpFetcher()
        retriever = EvidenceRetriever(providers=providers, fetcher=active_fetcher)
        return cls(
            claim_extractor=ClaimExtractor(),
            query_planner=QueryPlanner(),
            retriever=retriever,
            stance_classifier=StanceClassifier(),
            credibility_scorer=CredibilityScorer(),
            cross_examiner=cross_examiner,
        )

    @classmethod
    def with_fixture_provider(cls, providers: tuple[EvidenceProvider, ...]) -> "TextAnalysisPipeline":
        return cls.with_providers(providers)

    async def analyze(self, text: str, *, source_url: str | None = None) -> TextAnalysisResult:
        claim_extractor = (
            self.claim_extractor if source_url is None else ClaimExtractor(source_url=source_url)
        )
        claims = claim_extractor.extract(text)
        plans = self.query_planner.plan(claims)
        evidence = await self.retriever.retrieve(plans)
        stances = []
        scores = []
        for claim in claims:
            claim_evidence = tuple(item for item in evidence if item.claim_id == claim.id)
            if self.cross_examiner is None:
                classified = self.stance_classifier.classify(claim, claim_evidence)
            else:
                classified = await self.cross_examiner.classify(
                    claim,
                    claim_evidence,
                    self.stance_classifier,
                )
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
