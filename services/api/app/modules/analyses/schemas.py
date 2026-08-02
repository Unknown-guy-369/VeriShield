from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


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
    type: AnalysisType
    text: str | None = None
    source_url: AnyHttpUrl | None = None
    preferred_language: str = Field(default="en", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")

    @model_validator(mode="after")
    def validate_modality_fields(self) -> Self:
        if self.type is AnalysisType.TEXT:
            if self.text is None or len(self.text.strip()) < 10:
                raise ValueError("Text analyses require at least 10 characters of text.")
            self.text = self.text.strip()
            if self.source_url is not None:
                raise ValueError("Text analyses do not accept sourceUrl.")
        elif self.type is AnalysisType.URL:
            if self.source_url is None:
                raise ValueError("URL analyses require a valid HTTP or HTTPS sourceUrl.")
            if self.text is not None:
                raise ValueError("URL analyses do not accept text.")
        elif self.text is not None or self.source_url is not None:
            raise ValueError("Image and video analyses accept media files only.")
        return self


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
    type: AnalysisType
    preferred_language: str
    text: str | None = None
    source_url: str | None = None
    original_file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    storage_path: str | None = None
