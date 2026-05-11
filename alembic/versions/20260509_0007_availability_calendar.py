"""salon availability calendar

Revision ID: 20260509_0007
Revises: 20260509_0006
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0007"
down_revision: Union[str, None] = "20260509_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salon_availability_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("salon_id", sa.String(length=36), nullable=False),
        sa.Column("date", sa.DATE(), nullable=False),
        sa.Column("is_closed", sa.BOOLEAN(), nullable=False),
        sa.Column("open_time", sa.TIME(), nullable=True),
        sa.Column("close_time", sa.TIME(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("salon_id", "date", name="uq_salon_availability_override_date"),
    )
    op.create_index("ix_salon_availability_overrides_salon_id", "salon_availability_overrides", ["salon_id"])
    op.create_index("ix_salon_availability_overrides_date", "salon_availability_overrides", ["date"])
    op.create_index("ix_salon_availability_overrides_salon_date", "salon_availability_overrides", ["salon_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_salon_availability_overrides_salon_date", table_name="salon_availability_overrides")
    op.drop_index("ix_salon_availability_overrides_date", table_name="salon_availability_overrides")
    op.drop_index("ix_salon_availability_overrides_salon_id", table_name="salon_availability_overrides")
    op.drop_table("salon_availability_overrides")
