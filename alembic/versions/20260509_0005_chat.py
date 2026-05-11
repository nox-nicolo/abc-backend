"""customer salon chat

Revision ID: 20260509_0005
Revises: 20260509_0004
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0005"
down_revision: Union[str, None] = "20260509_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("salon_id", sa.String(length=36), nullable=False),
        sa.Column("salon_user_id", sa.String(length=36), nullable=False),
        sa.Column("last_message_preview", sa.String(length=500), nullable=True),
        sa.Column("last_message_type", sa.String(length=40), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_unread_count", sa.Integer(), nullable=False),
        sa.Column("salon_unread_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["salon_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "salon_id", name="uq_chat_customer_salon"),
    )
    op.create_index("ix_chat_conversations_id", "chat_conversations", ["id"])
    op.create_index("ix_chat_conversations_customer_last", "chat_conversations", ["customer_id", "last_message_at"])
    op.create_index("ix_chat_conversations_salon_user_last", "chat_conversations", ["salon_user_id", "last_message_at"])
    op.create_index("ix_chat_conversations_customer_id", "chat_conversations", ["customer_id"])
    op.create_index("ix_chat_conversations_salon_id", "chat_conversations", ["salon_id"])
    op.create_index("ix_chat_conversations_salon_user_id", "chat_conversations", ["salon_user_id"])
    op.create_index("ix_chat_conversations_last_message_at", "chat_conversations", ["last_message_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=True),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("message_type", sa.String(length=40), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_system", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_sender_user_id", "chat_messages", ["sender_user_id"])
    op.create_index("ix_chat_messages_booking_id", "chat_messages", ["booking_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
    op.create_index("ix_chat_messages_conversation_created", "chat_messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_conversation_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_booking_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_conversations_last_message_at", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_salon_user_id", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_salon_id", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_customer_id", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_salon_user_last", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_customer_last", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_id", table_name="chat_conversations")
    op.drop_table("chat_conversations")
