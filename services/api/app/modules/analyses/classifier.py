from dataclasses import dataclass
from urllib.parse import urlsplit

from app.modules.analyses.schemas import AnalysisType


@dataclass(frozen=True, slots=True)
class ClassifiedInput:
    type: AnalysisType
    text: str | None = None
    source_url: str | None = None


class InputClassifier:
    """Routes normalized intake without asking the user to choose a modality."""

    @staticmethod
    def classify_text(value: str) -> ClassifiedInput:
        parsed = urlsplit(value)
        is_public_url = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and not any(character.isspace() for character in value)
        )
        if is_public_url:
            return ClassifiedInput(type=AnalysisType.URL, source_url=value)
        return ClassifiedInput(type=AnalysisType.TEXT, text=value)

    @staticmethod
    def classify_media(mime_type: str, prompt: str | None) -> ClassifiedInput:
        analysis_type = (
            AnalysisType.IMAGE if mime_type.startswith("image/") else AnalysisType.VIDEO
        )
        return ClassifiedInput(type=analysis_type, text=prompt)
