import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey, Index, Text, Integer
from sqlalchemy.orm import relationship

from models.base import Base


class Notification(Base):
    """
    In-app notification row. Written at event time, read by the recipient
    whenever they open the app. No push delivery — that comes later.
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    recipient_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "like", "comment", "reply",
    # "booking_new", "booking_confirmed", "booking_rejected",
    # "booking_cancelled", "booking_completed", "booking_rescheduled"
    type = Column(String(40), nullable=False)
    message = Column(Text, nullable=True)

    post_id = Column(
        String(36),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    comment_id = Column(
        String(36),
        ForeignKey("post_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    booking_id = Column(
        String(36),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    is_read = Column(Boolean, default=False, nullable=False)
    delivery_status = Column(String(20), default="created", nullable=False, index=True)
    scheduled_for = Column(TIMESTAMP, nullable=True, index=True)
    created_at = Column(
        TIMESTAMP,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_id", "created_at"),
        Index("ix_notifications_recipient_unread", "recipient_id", "is_read"),
        Index("ix_notifications_recipient_read_created", "recipient_id", "is_read", "created_at"),
        Index("ix_notifications_recipient_status_created", "recipient_id", "delivery_status", "created_at"),
        Index("ix_notifications_actor_created", "actor_id", "created_at"),
    )


class NotificationSendLog(Base):
    """
    Durable guardrail for generated reminders. A cycle groups related sends,
    for example all reminders for one booking or one rebooking campaign.
    """
    __tablename__ = "notification_send_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_id = Column(String(36), ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True, index=True)
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True)
    cycle_key = Column(String(160), nullable=False, index=True)
    type = Column(String(40), nullable=False, index=True)
    message = Column(Text, nullable=False)
    send_count = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc), nullable=False)

    notification = relationship("Notification")
    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("ix_notification_send_logs_cycle", "cycle_key", "recipient_id", "type"),
        Index("ix_notification_send_logs_recipient_created", "recipient_id", "created_at"),
    )
