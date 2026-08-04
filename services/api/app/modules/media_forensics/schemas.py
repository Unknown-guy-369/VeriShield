from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.analyses.schemas import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SeverityLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Finding(ApiModel):
    code: str
    severity: SeverityLevel
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    explanation: str


class Region(ApiModel):
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)


class Timestamp(ApiModel):
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(ge=0.0)


class MediaAnalysisResult(ApiModel):
    analysis_id: UUID
    media_type: str
    manipulation_risk: float = Field(ge=0.0, le=1.0)
    confidence: ConfidenceLevel
    model_version: str
    findings: list[Finding] = Field(default_factory=list)
    suspicious_regions: list[Region] = Field(default_factory=list)
    suspicious_timestamps: list[Timestamp] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
