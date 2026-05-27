"""add profile media management fields

Revision ID: 20260527_0010
Revises: 20260527_0009
Create Date: 2026-05-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260527_0010"
down_revision: Union[str, None] = "20260527_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("salons", sa.Column("cover_position_x", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("salons", sa.Column("cover_position_y", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("salon_galleries", sa.Column("category", sa.String(length=60), nullable=False, server_default="general"))
    op.add_column("salon_galleries", sa.Column("position", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_salon_galleries_salon_position", "salon_galleries", ["salon_id", "position"], unique=False)
    op.create_index("ix_salon_galleries_salon_category", "salon_galleries", ["salon_id", "category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_salon_galleries_salon_category", table_name="salon_galleries")
    op.drop_index("ix_salon_galleries_salon_position", table_name="salon_galleries")
    op.drop_column("salon_galleries", "position")
    op.drop_column("salon_galleries", "category")
    op.drop_column("salons", "cover_position_y")
    op.drop_column("salons", "cover_position_x")
