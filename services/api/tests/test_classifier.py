from app.modules.analyses.classifier import InputClassifier
from app.modules.analyses.schemas import AnalysisType


def test_classifies_complete_http_url() -> None:
    result = InputClassifier.classify_text("https://example.com/public-post")

    assert result.type is AnalysisType.URL
    assert result.source_url == "https://example.com/public-post"
    assert result.text is None


def test_classifies_claim_containing_url_as_text() -> None:
    claim = "This post says https://example.com is reporting an election result."

    result = InputClassifier.classify_text(claim)

    assert result.type is AnalysisType.TEXT
    assert result.text == claim


def test_attachment_signature_takes_priority_over_prompt() -> None:
    result = InputClassifier.classify_media("video/mp4", "Check the speaker and lip sync.")

    assert result.type is AnalysisType.VIDEO
    assert result.text == "Check the speaker and lip sync."
