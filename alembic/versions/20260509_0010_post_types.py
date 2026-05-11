"""Add post types for service and announcement posts.

Revision ID: 20260509_0010
Revises: 20260509_0009
Create Date: 2026-05-09 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260509_0010"
down_revision = "20260509_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column(
            "post_type",
            sa.String(length=30),
            nullable=False,
            server_default="service",
        ),
    )
    op.create_index("ix_posts_post_type", "posts", ["post_type"])
    op.create_index("ix_posts_type_created", "posts", ["post_type", "created_at"])
    op.alter_column("posts", "post_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_posts_type_created", table_name="posts")
    op.drop_index("ix_posts_post_type", table_name="posts")
    op.drop_column("posts", "post_type")
