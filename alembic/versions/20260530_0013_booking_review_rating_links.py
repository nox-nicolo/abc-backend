"""booking review rating links

Revision ID: 20260530_0013
Revises: 20260527_0012
Create Date: 2026-05-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260530_0013"
down_revision: Union[str, None] = "20260527_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("stylist_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_bookings_stylist_id"), "bookings", ["stylist_id"], unique=False)
    op.create_foreign_key(
        "fk_bookings_stylist_id_salon_stylists",
        "bookings",
        "salon_stylists",
        ["stylist_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("service_reviews", sa.Column("service_id", sa.String(length=36), nullable=True))
    op.add_column("service_reviews", sa.Column("sub_service_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_service_reviews_service_id"), "service_reviews", ["service_id"], unique=False)
    op.create_index(op.f("ix_service_reviews_sub_service_id"), "service_reviews", ["sub_service_id"], unique=False)
    op.create_foreign_key(
        "fk_service_reviews_service_id_services",
        "service_reviews",
        "services",
        ["service_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_service_reviews_sub_service_id_sub_services",
        "service_reviews",
        "sub_services",
        ["sub_service_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_service_reviews_sub_service_id_sub_services", "service_reviews", type_="foreignkey")
    op.drop_constraint("fk_service_reviews_service_id_services", "service_reviews", type_="foreignkey")
    op.drop_index(op.f("ix_service_reviews_sub_service_id"), table_name="service_reviews")
    op.drop_index(op.f("ix_service_reviews_service_id"), table_name="service_reviews")
    op.drop_column("service_reviews", "sub_service_id")
    op.drop_column("service_reviews", "service_id")

    op.drop_constraint("fk_bookings_stylist_id_salon_stylists", "bookings", type_="foreignkey")
    op.drop_index(op.f("ix_bookings_stylist_id"), table_name="bookings")
    op.drop_column("bookings", "stylist_id")
