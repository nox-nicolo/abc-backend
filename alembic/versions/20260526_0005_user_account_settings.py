"""add user account settings

Revision ID: 20260526_0005
Revises: 20260519_0004
Create Date: 2026-05-26 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260526_0005"
down_revision: Union[str, None] = "20260519_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_account_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_account_settings_user_id"), "user_account_settings", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_account_settings_user_id"), table_name="user_account_settings")
    op.drop_table("user_account_settings")
