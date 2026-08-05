"""Provides the Ads database model module for the backend application."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from models.base import Base


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(String(36), primary_key=True, index=True)
    advertiser_name = Column(String(120), nullable=False)
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=True)
    cta_label = Column(String(40), default="Learn more", nullable=False)
    destination_url = Column(Text, nullable=False)
    media_url = Column(Text, nullable=False)
    media_type = Column(String(20), default="image", nullable=False)

    placement = Column(String(40), nullable=False, index=True)
    status = Column(String(24), default="draft", nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    weight = Column(Integer, default=1, nullable=False)

    target_country = Column(String(100), nullable=True, index=True)
    target_city = Column(String(100), nullable=True, index=True)
    target_category_id = Column(String(36), nullable=True, index=True)
    target_is_required = Column(Boolean, default=False, nullable=False)

    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    max_impressions = Column(Integer, nullable=True)
    max_clicks = Column(Integer, nullable=True)
    impression_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)

    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    events = relationship("AdEvent", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ad_campaigns_status_placement", "status", "placement"),
        Index("ix_ad_campaigns_active_window", "status", "starts_at", "ends_at"),
    )


class AdEvent(Base):
    __tablename__ = "ad_events"

    id = Column(String(36), primary_key=True, index=True)
    ad_id = Column(String(36), ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(24), nullable=False)
    placement = Column(String(40), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    campaign = relationship("AdCampaign", back_populates="events")

    __table_args__ = (
        Index("ix_ad_events_ad_type_created", "ad_id", "event_type", "created_at"),
        Index("ix_ad_events_user_created", "user_id", "created_at"),
    )
