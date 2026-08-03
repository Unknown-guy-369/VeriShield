from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class AnalysisType(StrEnum):
    TEXT = "TEXT"
    URL = "URL"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class AnalysisStatus(StrEnum):
    QUEUED = "QUEUED"
    PREPROCESSING = "PREPROCESSING"
    ANALYZING = "ANALYZING"
    RETRIEVING = "RETRIEVING"
    SCORING = "SCORING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CreateAnalysisRequest(ApiModel):
    input: str | None = None
    preferred_language: str = Field(default="en", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")

    @field_validator("input")
    @classmethod
    def normalize_input(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AnalysisRecord(ApiModel):
    id: UUID
    type: AnalysisType
    status: AnalysisStatus
    progress: int = Field(ge=0, le=100)
    preferred_language: str
    text: str | None = None
    source_url: str | None = None
    original_file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    storage_path: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateAnalysisData(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: AnalysisType
    preferred_language: str
    text: str | None = None
    source_url: str | None = None
    original_file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    storage_path: str | None = None
