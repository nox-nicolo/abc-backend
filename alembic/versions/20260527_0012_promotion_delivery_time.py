"""add promotion delivery time preferences

Revision ID: 20260527_0012
Revises: 20260527_0011
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260527_0012"
down_revision = "20260527_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_notification_preferences",
        sa.Column("promotions_preferred_time", sa.String(length=5), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("scheduled_for", sa.TIMESTAMP(), nullable=True),
    )
    op.create_index(
        op.f("ix_notifications_scheduled_for"),
        "notifications",
        ["scheduled_for"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_scheduled_for"), table_name="notifications")
    op.drop_column("notifications", "scheduled_for")
    op.drop_column("user_notification_preferences", "promotions_preferred_time")
