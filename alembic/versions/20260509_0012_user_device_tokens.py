"""Add user device tokens for push notifications.

Revision ID: 20260509_0012
Revises: 20260509_0011
Create Date: 2026-05-09 00:12:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260509_0012"
down_revision = "20260509_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_device_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("push_provider", sa.String(length=30), nullable=False, server_default="fcm"),
        sa.Column("push_token", sa.String(length=512), nullable=False),
        sa.Column("app_version", sa.String(length=80), nullable=True),
        sa.Column("build_number", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_user_device_tokens_user_device"),
    )
    op.create_index("ix_user_device_tokens_user_id", "user_device_tokens", ["user_id"])
    op.create_index("ix_user_device_tokens_token", "user_device_tokens", ["push_token"])
    op.create_index("ix_user_device_tokens_user_active", "user_device_tokens", ["user_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_user_device_tokens_user_active", table_name="user_device_tokens")
    op.drop_index("ix_user_device_tokens_token", table_name="user_device_tokens")
    op.drop_index("ix_user_device_tokens_user_id", table_name="user_device_tokens")
    op.drop_table("user_device_tokens")
