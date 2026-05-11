"""user mutes

Revision ID: 20260509_0008
Revises: 20260509_0007
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0008"
down_revision: Union[str, None] = "20260509_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_mutes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_mute_target"),
    )
    op.create_index("ix_user_mutes_user_id", "user_mutes", ["user_id"])
    op.create_index("ix_user_mutes_target_type", "user_mutes", ["target_type"])
    op.create_index("ix_user_mutes_target_id", "user_mutes", ["target_id"])
    op.create_index("ix_user_mutes_user_type_created", "user_mutes", ["user_id", "target_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_mutes_user_type_created", table_name="user_mutes")
    op.drop_index("ix_user_mutes_target_id", table_name="user_mutes")
    op.drop_index("ix_user_mutes_target_type", table_name="user_mutes")
    op.drop_index("ix_user_mutes_user_id", table_name="user_mutes")
    op.drop_table("user_mutes")
