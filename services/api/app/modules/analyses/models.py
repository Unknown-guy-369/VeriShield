from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.modules.analyses.schemas import AnalysisStatus, AnalysisType

SCHEMA = "verishield_private"


def utc_now() -> datetime:
    return datetime.now(UTC)


class AnalysisModel(Base):
    __tablename__ = "analyses"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType, name="AnalysisType", schema=SCHEMA),
        nullable=False,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="AnalysisStatus", schema=SCHEMA),
        nullable=False,
        default=AnalysisStatus.QUEUED,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    preferred_language: Mapped[str] = mapped_column(String(35), nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    original_file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(Integer)
    storage_path: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
