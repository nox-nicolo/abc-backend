"""add ad campaigns

Revision ID: 20260519_0004
Revises: 20260515_0003
Create Date: 2026-05-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0004"
down_revision: Union[str, None] = "20260515_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("advertiser_name", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("cta_label", sa.String(length=40), nullable=False),
        sa.Column("destination_url", sa.Text(), nullable=False),
        sa.Column("media_url", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("placement", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("target_country", sa.String(length=100), nullable=True),
        sa.Column("target_city", sa.String(length=100), nullable=True),
        sa.Column("target_category_id", sa.String(length=36), nullable=True),
        sa.Column("target_is_required", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_impressions", sa.Integer(), nullable=True),
        sa.Column("max_clicks", sa.Integer(), nullable=True),
        sa.Column("impression_count", sa.Integer(), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ad_campaigns_id"), "ad_campaigns", ["id"], unique=False)
    op.create_index("ix_ad_campaigns_active_window", "ad_campaigns", ["status", "starts_at", "ends_at"], unique=False)
    op.create_index("ix_ad_campaigns_status_placement", "ad_campaigns", ["status", "placement"], unique=False)
    op.create_index(op.f("ix_ad_campaigns_placement"), "ad_campaigns", ["placement"], unique=False)
    op.create_index(op.f("ix_ad_campaigns_status"), "ad_campaigns", ["status"], unique=False)
    op.create_index(op.f("ix_ad_campaigns_target_category_id"), "ad_campaigns", ["target_category_id"], unique=False)
    op.create_index(op.f("ix_ad_campaigns_target_city"), "ad_campaigns", ["target_city"], unique=False)
    op.create_index(op.f("ix_ad_campaigns_target_country"), "ad_campaigns", ["target_country"], unique=False)

    op.create_table(
        "ad_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ad_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("placement", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ad_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ad_events_id"), "ad_events", ["id"], unique=False)
    op.create_index("ix_ad_events_ad_type_created", "ad_events", ["ad_id", "event_type", "created_at"], unique=False)
    op.create_index("ix_ad_events_user_created", "ad_events", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ad_events_user_created", table_name="ad_events")
    op.drop_index("ix_ad_events_ad_type_created", table_name="ad_events")
    op.drop_index(op.f("ix_ad_events_id"), table_name="ad_events")
    op.drop_table("ad_events")
    op.drop_index(op.f("ix_ad_campaigns_target_country"), table_name="ad_campaigns")
    op.drop_index(op.f("ix_ad_campaigns_target_city"), table_name="ad_campaigns")
    op.drop_index(op.f("ix_ad_campaigns_target_category_id"), table_name="ad_campaigns")
    op.drop_index(op.f("ix_ad_campaigns_status"), table_name="ad_campaigns")
    op.drop_index(op.f("ix_ad_campaigns_placement"), table_name="ad_campaigns")
    op.drop_index("ix_ad_campaigns_status_placement", table_name="ad_campaigns")
    op.drop_index("ix_ad_campaigns_active_window", table_name="ad_campaigns")
    op.drop_index(op.f("ix_ad_campaigns_id"), table_name="ad_campaigns")
    op.drop_table("ad_campaigns")
