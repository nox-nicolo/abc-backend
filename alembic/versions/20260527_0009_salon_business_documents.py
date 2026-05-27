"""add salon business documents

Revision ID: 20260527_0009
Revises: 20260527_0008
Create Date: 2026-05-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260527_0009"
down_revision: Union[str, None] = "20260527_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salon_business_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("salon_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("document_type", sa.String(length=60), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_salon_business_documents_id"), "salon_business_documents", ["id"], unique=False)
    op.create_index(op.f("ix_salon_business_documents_salon_id"), "salon_business_documents", ["salon_id"], unique=False)
    op.create_index(op.f("ix_salon_business_documents_uploaded_by_user_id"), "salon_business_documents", ["uploaded_by_user_id"], unique=False)
    op.create_index(op.f("ix_salon_business_documents_review_status"), "salon_business_documents", ["review_status"], unique=False)
    op.create_index("ix_salon_business_documents_salon_status", "salon_business_documents", ["salon_id", "review_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_salon_business_documents_salon_status", table_name="salon_business_documents")
    op.drop_index(op.f("ix_salon_business_documents_review_status"), table_name="salon_business_documents")
    op.drop_index(op.f("ix_salon_business_documents_uploaded_by_user_id"), table_name="salon_business_documents")
    op.drop_index(op.f("ix_salon_business_documents_salon_id"), table_name="salon_business_documents")
    op.drop_index(op.f("ix_salon_business_documents_id"), table_name="salon_business_documents")
    op.drop_table("salon_business_documents")
