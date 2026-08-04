import asyncio
from app.modules.analyses.text_pipeline.pipeline import TextAnalysisPipeline
from app.modules.analyses.text_pipeline.providers.fixture import FixtureEvidenceProvider

async def main():
    pipeline = TextAnalysisPipeline.with_fixture_provider(providers=(FixtureEvidenceProvider(),))
    
    # Just a test text if we can't get the DB right now
    text = "The earth is flat."
    print("Running pipeline...")
    result = await pipeline.analyze(text)
    print("Pipeline result:")
    print("Claims:", result.claims)
    print("Evidence:", len(result.evidence), "items")
    print("Stances:", result.stances)
    print("Scores:", result.scores)

if __name__ == "__main__":
    asyncio.run(main())
