"""service reviews for completed bookings

Revision ID: 20260509_0004
Revises: 20260509_0003
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260509_0004"
down_revision: Union[str, None] = "20260509_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("service_reviews"):
        op.create_table(
            "service_reviews",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("booking_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("salon_id", sa.String(length=36), nullable=False),
            sa.Column("salon_service_price_id", sa.String(length=36), nullable=False),
            sa.Column("stylist_id", sa.String(length=36), nullable=True),
            sa.Column("rating", sa.INTEGER(), nullable=False),
            sa.Column("comment", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["salon_service_price_id"], ["salon_service_prices.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stylist_id"], ["salon_stylists.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("booking_id", name="uq_service_reviews_booking"),
        )
        inspector = inspect(bind)

    indexes = {
        "ix_service_reviews_id": ["id"],
        "ix_service_reviews_booking_id": ["booking_id"],
        "ix_service_reviews_user_id": ["user_id"],
        "ix_service_reviews_salon_id": ["salon_id"],
        "ix_service_reviews_salon_service_price_id": ["salon_service_price_id"],
        "ix_service_reviews_stylist_id": ["stylist_id"],
        "ix_service_reviews_salon_created": ["salon_id", "created_at"],
        "ix_service_reviews_service_created": ["salon_service_price_id", "created_at"],
    }
    for name, columns in indexes.items():
        if not _has_index(inspector, "service_reviews", name):
            op.create_index(name, "service_reviews", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("service_reviews"):
        return

    for name in (
        "ix_service_reviews_service_created",
        "ix_service_reviews_salon_created",
        "ix_service_reviews_stylist_id",
        "ix_service_reviews_salon_service_price_id",
        "ix_service_reviews_salon_id",
        "ix_service_reviews_user_id",
        "ix_service_reviews_booking_id",
        "ix_service_reviews_id",
    ):
        if _has_index(inspector, "service_reviews", name):
            op.drop_index(name, table_name="service_reviews")
    op.drop_table("service_reviews")
