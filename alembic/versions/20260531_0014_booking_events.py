"""add booking lifecycle events

Revision ID: 20260531_0014
Revises: 20260530_0013
Create Date: 2026-05-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260531_0014"
down_revision: Union[str, None] = "20260530_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_events_id"), "booking_events", ["id"], unique=False)
    op.create_index(op.f("ix_booking_events_booking_id"), "booking_events", ["booking_id"], unique=False)
    op.create_index(op.f("ix_booking_events_actor_id"), "booking_events", ["actor_id"], unique=False)
    op.create_index(op.f("ix_booking_events_event_type"), "booking_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_booking_events_created_at"), "booking_events", ["created_at"], unique=False)
    op.create_index("ix_booking_events_booking_created", "booking_events", ["booking_id", "created_at"], unique=False)
    op.create_index("ix_booking_events_booking_type", "booking_events", ["booking_id", "event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_booking_events_booking_type", table_name="booking_events")
    op.drop_index("ix_booking_events_booking_created", table_name="booking_events")
    op.drop_index(op.f("ix_booking_events_created_at"), table_name="booking_events")
    op.drop_index(op.f("ix_booking_events_event_type"), table_name="booking_events")
    op.drop_index(op.f("ix_booking_events_actor_id"), table_name="booking_events")
    op.drop_index(op.f("ix_booking_events_booking_id"), table_name="booking_events")
    op.drop_index(op.f("ix_booking_events_id"), table_name="booking_events")
    op.drop_table("booking_events")
