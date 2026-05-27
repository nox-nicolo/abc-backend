"""add user audit events

Revision ID: 20260526_0007
Revises: 20260526_0005
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260526_0007"
down_revision = "20260526_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_audit_events_user_id"), "user_audit_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_audit_events_event_type"), "user_audit_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_user_audit_events_created_at"), "user_audit_events", ["created_at"], unique=False)
    op.create_index("ix_user_audit_events_user_created", "user_audit_events", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_audit_events_user_created", table_name="user_audit_events")
    op.drop_index(op.f("ix_user_audit_events_created_at"), table_name="user_audit_events")
    op.drop_index(op.f("ix_user_audit_events_event_type"), table_name="user_audit_events")
    op.drop_index(op.f("ix_user_audit_events_user_id"), table_name="user_audit_events")
    op.drop_table("user_audit_events")
