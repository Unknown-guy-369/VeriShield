from __future__ import annotations

from datetime import UTC, datetime

from app.modules.analyses.text_pipeline import (
    ClaimExtractor,
    CredibilityScorer,
    EvidenceProvider,
    EvidenceStance,
    EvidenceItem,
    EvidenceRetriever,
    FixtureEvidenceProvider,
    QueryPlanner,
    ClaimRecord,
    SecureHttpFetcher,
    StanceClassifier,
    TextAnalysisPipeline,
)
from app.modules.analyses.text_pipeline.evidence_retriever import TextPipelineError
from app.modules.analyses.text_pipeline.schemas import ClaimQueryPlan, PlannedQuery, SearchResult
import pytest


class DuplicateEvidenceProvider(EvidenceProvider):
    name = "duplicate"

    async def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        now = datetime(2026, 8, 3, tzinfo=UTC)
        result = SearchResult(
            title="Example Government Notice",
            url="https://example.gov.in/notice",
            snippet="The government announced the program.",
            publisher="Example Government",
            published_at=now,
            relevance_hint=0.9,
            provider_name=self.name,
            fetchable=False,
        )
        return (result, result)


class StaticFetcher:
    async def fetch(self, url: str) -> tuple[str, str | None, datetime | None, str]:
        return "Fetched title", "Fetched publisher", datetime(2026, 8, 3, tzinfo=UTC), "Fetched passage"


def test_extracts_fact_claims_and_skips_questions_and_opinions() -> None:
    extractor = ClaimExtractor(source_url="https://example.com/post")
    claims = extractor.extract(
        "The government announced free laptops for eligible students. "
        "I think this is a great idea. "
        "Is the announcement confirmed?"
    )

    assert len(claims) == 1
    assert claims[0].normalized_text == "the government announced free laptops for eligible students"
    assert "government" in " ".join(claims[0].entities).lower()
    assert claims[0].source_url == "https://example.com/post"


def test_plans_multiple_search_queries_for_each_claim() -> None:
    claim = ClaimRecord(
        id="claim-1",
        index=0,
        text="The government announced free laptops for eligible students.",
        normalized_text="the government announced free laptops for eligible students",
        entities=("government", "free laptops"),
    )
    planner = QueryPlanner()
    plans = planner.plan((claim,))

    assert len(plans) == 1
    assert len(plans[0].queries) == 5
    assert plans[0].queries[0].query.startswith("The government announced")
    assert "fact_check" in plans[0].queries[1].provider_hints


@pytest.mark.asyncio
async def test_retriever_deduplicates_identical_articles() -> None:
    retriever = EvidenceRetriever(
        providers=(DuplicateEvidenceProvider(),),
        fetcher=StaticFetcher(),
    )
    plan = ClaimQueryPlan(
        claim_id="claim-1",
        queries=(PlannedQuery(query="government notice"), PlannedQuery(query="government announcement")),
    )

    evidence = await retriever.retrieve((plan,))

    assert len(evidence) == 1
    assert evidence[0].canonical_url == "https://example.gov.in/notice"
    assert evidence[0].retrieval_confidence > 0.5


def test_secure_fetcher_blocks_private_urls() -> None:
    fetcher = SecureHttpFetcher()

    with pytest.raises(TextPipelineError) as error:
        fetcher._validate_public_http_url("http://127.0.0.1/private")

    assert error.value.code == "PRIVATE_URL_BLOCKED"


def test_stance_and_scoring_are_deterministic() -> None:
    claim = ClaimRecord(
        id="claim-1",
        index=0,
        text="The government announced free laptops for eligible students.",
        normalized_text="the government announced free laptops for eligible students",
        entities=("government", "free laptops"),
    )
    evidence = (
        EvidenceItem(
            id="e1",
            claim_id="claim-1",
            stance=EvidenceStance.INSUFFICIENT,
            title="Government confirms free laptop rollout for eligible students",
            publisher="Department of Education",
            url="https://state.gov.in/education/free-laptops-announcement",
            published_at=datetime(2026, 8, 3, tzinfo=UTC),
            passage="The department announced a phased laptop distribution program for eligible students.",
            relevance=0.9,
            source_reliability=95,
            retrieval_confidence=0.92,
            provider_name="fixture",
            query="free laptop",
            canonical_url="https://state.gov.in/education/free-laptops-announcement",
            dedupe_key="dedupe-1",
        ),
    )
    classifier = StanceClassifier()
    classified = classifier.classify(claim, evidence)
    summary = classifier.summarize(claim, classified)
    score = CredibilityScorer().score(claim, classified)

    assert classified[0].stance is EvidenceStance.SUPPORTED
    assert summary.stance is EvidenceStance.SUPPORTED
    assert score.score >= 70
    assert "score = clamp" in score.formula


@pytest.mark.asyncio
async def test_pipeline_runs_with_fixture_provider() -> None:
    pipeline = TextAnalysisPipeline.with_fixture_provider((FixtureEvidenceProvider(),))
    result = await pipeline.analyze(
        "The government announced free laptops for eligible students. This should be checked carefully."
    )

    assert len(result.claims) >= 1
    assert len(result.evidence) >= 1
    assert all(score.score >= 0 for score in result.scores)
