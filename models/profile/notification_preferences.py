import uuid
from datetime import datetime, timezone

from sqlalchemy import BOOLEAN, Column, DateTime, ForeignKey, INTEGER, String
from sqlalchemy.orm import relationship

from models.base import Base


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    allow_likes = Column(BOOLEAN, nullable=False, default=True)
    allow_comments = Column(BOOLEAN, nullable=False, default=True)
    allow_bookings = Column(BOOLEAN, nullable=False, default=True)
    allow_promotions = Column(BOOLEAN, nullable=False, default=True)
    promotions_preferred_time = Column(String(5), nullable=True)

    # Booking reminder preferences — apply to both salon owners and customers.
    allow_reminders = Column(BOOLEAN, nullable=False, default=True)
    reminder_lead_minutes = Column(INTEGER, nullable=False, default=30)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User")
