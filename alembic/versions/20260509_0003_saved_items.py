"""saved salons and services

Revision ID: 20260509_0003
Revises: 20260508_0002
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0003"
down_revision: Union[str, None] = "20260508_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_salons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("salon_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "salon_id", name="uq_saved_salons_user_salon"),
    )
    op.create_index("ix_saved_salons_id", "saved_salons", ["id"])
    op.create_index("ix_saved_salons_user_created", "saved_salons", ["user_id", "created_at"])
    op.create_index("ix_saved_salons_salon_created", "saved_salons", ["salon_id", "created_at"])

    op.create_table(
        "saved_services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=True),
        sa.Column("sub_service_id", sa.String(length=36), nullable=True),
        sa.Column("salon_service_price_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["salon_service_price_id"], ["salon_service_prices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sub_service_id"], ["sub_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "service_id", name="uq_saved_services_user_service"),
        sa.UniqueConstraint("user_id", "sub_service_id", name="uq_saved_services_user_sub_service"),
        sa.UniqueConstraint("user_id", "salon_service_price_id", name="uq_saved_services_user_salon_price"),
    )
    op.create_index("ix_saved_services_id", "saved_services", ["id"])
    op.create_index("ix_saved_services_user_created", "saved_services", ["user_id", "created_at"])
    op.create_index("ix_saved_services_service_created", "saved_services", ["service_id", "created_at"])
    op.create_index("ix_saved_services_sub_service_created", "saved_services", ["sub_service_id", "created_at"])
    op.create_index("ix_saved_services_salon_price_created", "saved_services", ["salon_service_price_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_saved_services_salon_price_created", table_name="saved_services")
    op.drop_index("ix_saved_services_sub_service_created", table_name="saved_services")
    op.drop_index("ix_saved_services_service_created", table_name="saved_services")
    op.drop_index("ix_saved_services_user_created", table_name="saved_services")
    op.drop_index("ix_saved_services_id", table_name="saved_services")
    op.drop_table("saved_services")

    op.drop_index("ix_saved_salons_salon_created", table_name="saved_salons")
    op.drop_index("ix_saved_salons_user_created", table_name="saved_salons")
    op.drop_index("ix_saved_salons_id", table_name="saved_salons")
    op.drop_table("saved_salons")
