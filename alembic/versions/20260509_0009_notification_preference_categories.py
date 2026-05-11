"""notification preference categories

Revision ID: 20260509_0009
Revises: 20260509_0008
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0009"
down_revision: Union[str, None] = "20260509_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_notification_preferences", sa.Column("allow_likes", sa.BOOLEAN(), nullable=False, server_default=sa.true()))
    op.add_column("user_notification_preferences", sa.Column("allow_comments", sa.BOOLEAN(), nullable=False, server_default=sa.true()))
    op.add_column("user_notification_preferences", sa.Column("allow_bookings", sa.BOOLEAN(), nullable=False, server_default=sa.true()))
    op.add_column("user_notification_preferences", sa.Column("allow_promotions", sa.BOOLEAN(), nullable=False, server_default=sa.true()))
    op.alter_column("user_notification_preferences", "allow_likes", server_default=None)
    op.alter_column("user_notification_preferences", "allow_comments", server_default=None)
    op.alter_column("user_notification_preferences", "allow_bookings", server_default=None)
    op.alter_column("user_notification_preferences", "allow_promotions", server_default=None)


def downgrade() -> None:
    op.drop_column("user_notification_preferences", "allow_promotions")
    op.drop_column("user_notification_preferences", "allow_bookings")
    op.drop_column("user_notification_preferences", "allow_comments")
    op.drop_column("user_notification_preferences", "allow_likes")
