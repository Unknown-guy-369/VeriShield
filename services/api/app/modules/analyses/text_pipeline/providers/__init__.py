from app.modules.analyses.text_pipeline.providers.base import EvidenceProvider
from app.modules.analyses.text_pipeline.providers.fixture import FixtureEvidenceProvider
from app.modules.analyses.text_pipeline.providers.google_fact_check import GoogleFactCheckProvider

__all__ = [
    "EvidenceProvider",
    "FixtureEvidenceProvider",
    "GoogleFactCheckProvider",
]
