"""Provides the Insights database model module for profile workflows."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String

from models.base import Base


class SalonInsightEvent(Base):
    __tablename__ = "salon_insight_events"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(40), nullable=False, index=True)
    target_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("ix_salon_insight_event_lookup", "salon_id", "event_type", "created_at"),
        Index("ix_salon_insight_event_target", "salon_id", "event_type", "target_id"),
    )
