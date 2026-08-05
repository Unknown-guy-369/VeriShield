"""Add result column to analyses.

Revision ID: 20260804_0001
Revises: 20260802_0001
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260804_0001"
down_revision: str | Sequence[str] | None = "20260802_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="verishield_private",
    )


def downgrade() -> None:
    op.drop_column("analyses", "result", schema="verishield_private")
