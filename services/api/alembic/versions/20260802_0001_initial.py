"""Create the private analysis intake schema.

Revision ID: 20260802_0001
Revises:
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260802_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "verishield_private"')
    op.execute(
        """
        CREATE TYPE "verishield_private"."AnalysisType"
        AS ENUM ('TEXT', 'URL', 'IMAGE', 'VIDEO')
        """
    )
    op.execute(
        """
        CREATE TYPE "verishield_private"."AnalysisStatus"
        AS ENUM ('QUEUED', 'PREPROCESSING', 'ANALYZING', 'RETRIEVING',
                 'SCORING', 'COMPLETED', 'FAILED')
        """
    )
    op.execute(
        """
        CREATE TABLE "verishield_private"."analyses" (
          "id" UUID PRIMARY KEY,
          "type" "verishield_private"."AnalysisType" NOT NULL,
          "status" "verishield_private"."AnalysisStatus" NOT NULL DEFAULT 'QUEUED',
          "progress" INTEGER NOT NULL DEFAULT 10,
          "preferred_language" VARCHAR(35) NOT NULL,
          "text" TEXT,
          "source_url" TEXT,
          "original_file_name" VARCHAR(255),
          "mime_type" VARCHAR(100),
          "file_size" INTEGER,
          "storage_path" TEXT,
          "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
          "updated_at" TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "verishield_private"."analyses"')
    op.execute('DROP TYPE IF EXISTS "verishield_private"."AnalysisStatus"')
    op.execute('DROP TYPE IF EXISTS "verishield_private"."AnalysisType"')
    op.execute('DROP SCHEMA IF EXISTS "verishield_private"')
