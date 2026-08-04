"""Add result column to analyses

Revision ID: 20260804_0001
Revises: 20260802_0001
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260804_0001'
down_revision = '20260802_0001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We update the DB bypassing the missing revision
    op.execute("UPDATE alembic_version SET version_num='20260802_0001' WHERE version_num='20260803_0002'")
    op.add_column('analyses', sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='verishield_private')

def downgrade() -> None:
    op.drop_column('analyses', 'result', schema='verishield_private')
