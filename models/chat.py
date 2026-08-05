"""Provides the Chat database model module for the backend application."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from models.base import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)
    salon_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    last_message_preview = Column(String(500), nullable=True)
    last_message_type = Column(String(40), nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)

    customer_unread_count = Column(Integer, nullable=False, default=0)
    salon_unread_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    customer = relationship("User", foreign_keys=[customer_id])
    salon_user = relationship("User", foreign_keys=[salon_user_id])
    salon = relationship("Salon")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        UniqueConstraint("customer_id", "salon_id", name="uq_chat_customer_salon"),
        Index("ix_chat_conversations_customer_last", "customer_id", "last_message_at"),
        Index("ix_chat_conversations_salon_user_last", "salon_user_id", "last_message_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String(36),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sender_role = Column(String(20), nullable=False)  # customer | salon | system
    message_type = Column(String(40), nullable=False, default="text")
    body = Column(Text, nullable=False)
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_system = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    conversation = relationship("ChatConversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_user_id])
    booking = relationship("Booking")

    __table_args__ = (
        Index("ix_chat_messages_conversation_created", "conversation_id", "created_at"),
    )
