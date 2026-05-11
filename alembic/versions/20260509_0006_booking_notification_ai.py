"""booking notification ai messages

Revision ID: 20260509_0006
Revises: 20260509_0005
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0006"
down_revision: Union[str, None] = "20260509_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("message", sa.Text(), nullable=True))
    op.alter_column("notifications", "type", existing_type=sa.String(length=24), type_=sa.String(length=40), existing_nullable=False)

    op.create_table(
        "notification_send_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("recipient_id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("notification_id", sa.String(length=36), nullable=True),
        sa.Column("booking_id", sa.String(length=36), nullable=True),
        sa.Column("cycle_key", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("send_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_send_logs_actor_id", "notification_send_logs", ["actor_id"])
    op.create_index("ix_notification_send_logs_booking_id", "notification_send_logs", ["booking_id"])
    op.create_index("ix_notification_send_logs_cycle", "notification_send_logs", ["cycle_key", "recipient_id", "type"])
    op.create_index("ix_notification_send_logs_cycle_key", "notification_send_logs", ["cycle_key"])
    op.create_index("ix_notification_send_logs_notification_id", "notification_send_logs", ["notification_id"])
    op.create_index("ix_notification_send_logs_recipient_created", "notification_send_logs", ["recipient_id", "created_at"])
    op.create_index("ix_notification_send_logs_recipient_id", "notification_send_logs", ["recipient_id"])
    op.create_index("ix_notification_send_logs_type", "notification_send_logs", ["type"])


def downgrade() -> None:
    op.drop_index("ix_notification_send_logs_type", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_recipient_id", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_recipient_created", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_notification_id", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_cycle_key", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_cycle", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_booking_id", table_name="notification_send_logs")
    op.drop_index("ix_notification_send_logs_actor_id", table_name="notification_send_logs")
    op.drop_table("notification_send_logs")

    op.alter_column("notifications", "type", existing_type=sa.String(length=40), type_=sa.String(length=24), existing_nullable=False)
    op.drop_column("notifications", "message")
