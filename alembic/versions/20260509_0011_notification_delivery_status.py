"""Add delivery status to notifications.

Revision ID: 20260509_0011
Revises: 20260509_0010
Create Date: 2026-05-09 00:11:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260509_0011"
down_revision = "20260509_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "delivery_status",
            sa.String(length=20),
            nullable=False,
            server_default="sent",
        ),
    )
    op.execute(
        "UPDATE notifications SET delivery_status = CASE WHEN is_read THEN 'read' ELSE 'sent' END"
    )
    op.create_index("ix_notifications_delivery_status", "notifications", ["delivery_status"])
    op.create_index(
        "ix_notifications_recipient_status_created",
        "notifications",
        ["recipient_id", "delivery_status", "created_at"],
    )
    op.alter_column("notifications", "delivery_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_status_created", table_name="notifications")
    op.drop_index("ix_notifications_delivery_status", table_name="notifications")
    op.drop_column("notifications", "delivery_status")
