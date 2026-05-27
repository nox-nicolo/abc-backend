"""add mute reason

Revision ID: 20260527_0011
Revises: 20260527_0010
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260527_0011"
down_revision = "20260527_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_mutes", sa.Column("reason", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("user_mutes", "reason")
