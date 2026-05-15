"""add post reactions and comment likes

Revision ID: 20260515_0003
Revises: 20260514_0002
Create Date: 2026-05-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0003"
down_revision: Union[str, None] = "20260514_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_reactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reaction", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_post_reactions_id"), "post_reactions", ["id"], unique=False)
    op.create_index(
        "ix_post_reactions_post_reaction",
        "post_reactions",
        ["post_id", "reaction"],
        unique=False,
    )
    op.create_index(
        "ix_post_reactions_post_user",
        "post_reactions",
        ["post_id", "user_id"],
        unique=True,
    )

    op.create_table(
        "post_comment_likes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("comment_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("liked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["post_comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_post_comment_likes_id"), "post_comment_likes", ["id"], unique=False)
    op.create_index(
        "ix_post_comment_likes_comment_liked",
        "post_comment_likes",
        ["comment_id", "liked"],
        unique=False,
    )
    op.create_index(
        "ix_post_comment_likes_comment_user",
        "post_comment_likes",
        ["comment_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_post_comment_likes_comment_user", table_name="post_comment_likes")
    op.drop_index("ix_post_comment_likes_comment_liked", table_name="post_comment_likes")
    op.drop_index(op.f("ix_post_comment_likes_id"), table_name="post_comment_likes")
    op.drop_table("post_comment_likes")
    op.drop_index("ix_post_reactions_post_user", table_name="post_reactions")
    op.drop_index("ix_post_reactions_post_reaction", table_name="post_reactions")
    op.drop_index(op.f("ix_post_reactions_id"), table_name="post_reactions")
    op.drop_table("post_reactions")
