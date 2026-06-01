"""fix search history ids

Revision ID: 20260531_0015
Revises: 20260531_0014
Create Date: 2026-05-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260531_0015"
down_revision: Union[str, None] = "20260531_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("search_histories", "entity_id", existing_type=sa.Integer(), type_=sa.String(length=64), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("search_histories", "entity_id", existing_type=sa.String(length=64), type_=sa.Integer(), existing_nullable=True)
