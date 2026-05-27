"""add salon insight events

Revision ID: 20260527_0008
Revises: 20260526_0007
Create Date: 2026-05-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260527_0008"
down_revision: Union[str, None] = "20260526_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salon_insight_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("salon_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_salon_insight_events_id"), "salon_insight_events", ["id"], unique=False)
    op.create_index(op.f("ix_salon_insight_events_salon_id"), "salon_insight_events", ["salon_id"], unique=False)
    op.create_index(op.f("ix_salon_insight_events_user_id"), "salon_insight_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_salon_insight_events_event_type"), "salon_insight_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_salon_insight_events_target_id"), "salon_insight_events", ["target_id"], unique=False)
    op.create_index(op.f("ix_salon_insight_events_created_at"), "salon_insight_events", ["created_at"], unique=False)
    op.create_index("ix_salon_insight_event_lookup", "salon_insight_events", ["salon_id", "event_type", "created_at"], unique=False)
    op.create_index("ix_salon_insight_event_target", "salon_insight_events", ["salon_id", "event_type", "target_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_salon_insight_event_target", table_name="salon_insight_events")
    op.drop_index("ix_salon_insight_event_lookup", table_name="salon_insight_events")
    op.drop_index(op.f("ix_salon_insight_events_created_at"), table_name="salon_insight_events")
    op.drop_index(op.f("ix_salon_insight_events_target_id"), table_name="salon_insight_events")
    op.drop_index(op.f("ix_salon_insight_events_event_type"), table_name="salon_insight_events")
    op.drop_index(op.f("ix_salon_insight_events_user_id"), table_name="salon_insight_events")
    op.drop_index(op.f("ix_salon_insight_events_salon_id"), table_name="salon_insight_events")
    op.drop_index(op.f("ix_salon_insight_events_id"), table_name="salon_insight_events")
    op.drop_table("salon_insight_events")
