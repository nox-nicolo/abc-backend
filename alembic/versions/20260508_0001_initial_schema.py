"""initial schema

Revision ID: 20260508_0001
Revises:
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op

from models.base import Base
import models.registry  # noqa: F401

revision: str = "20260508_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
