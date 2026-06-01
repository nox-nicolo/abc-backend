import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    INTEGER, Column, DateTime, Index, String, ForeignKey, Enum, TIMESTAMP,
    Integer, JSON, Numeric, Text
)
from sqlalchemy.orm import relationship

from core.enumeration import BookingStatus, ImageURL
from models.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    customer_id = Column( String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,  index=True)

    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)

    salon_service_price_id = Column(String(36), ForeignKey("salon_service_prices.id", ondelete="SET NULL"), nullable=True, index=True)

    stylist_id = Column(String(36), ForeignKey("salon_stylists.id", ondelete="SET NULL"), nullable=True, index=True)

    # schedule
    start_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    end_at = Column(TIMESTAMP(timezone=True), nullable=False)

    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING, index=True)

    service_name_snapshot = Column(String(120), nullable=True)
    price_snapshot = Column(Numeric(12, 2), nullable=False)
    currency_snapshot = Column(String(10), nullable=False)
    duration_minutes_snapshot = Column(Integer, nullable=False)

    # optional notes
    note = Column(Text, nullable=True)

    # cancellation tracking
    cancelled_by = Column(String(10), nullable=True)  # "user" | "salon"
    cancel_reason = Column(String(255), nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False)

    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # relationships
    customer = relationship("User", back_populates="bookings")
    salon = relationship("Salon", back_populates="bookings")
    salon_service_price = relationship("SalonServicePrice", back_populates="bookings")
    stylist = relationship("SalonStylist")
    review = relationship(
        "ServiceReview",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )
    events = relationship(
        "BookingEvent",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="BookingEvent.created_at",
    )

    @property
    def customer_name(self):
        return self.customer.name if self.customer else None

    @property
    def stylist_name(self):
        if not self.stylist:
            return None
        if self.stylist.user:
            return self.stylist.user.name
        return self.stylist.title

    @property
    def stylist_avatar(self):
        if not self.stylist or not self.stylist.user:
            return None
        profile_picture = self.stylist.user.profile_picture
        if not profile_picture or not profile_picture.file_name:
            return None
        return f"{ImageURL.PROFILE_URL.value}/{profile_picture.file_name}"

    @property
    def has_review(self):
        return self.review is not None

    @property
    def review_rating(self):
        return self.review.rating if self.review else None

    @property
    def review_comment(self):
        return self.review.comment if self.review else None

    @property
    def review_created_at(self):
        return self.review.created_at if self.review else None

    __table_args__ = (
        Index("ix_bookings_customer_status_start", "customer_id", "status", "start_at"),
        Index("ix_bookings_salon_status_start", "salon_id", "status", "start_at"),
        Index("ix_bookings_service_status_start", "salon_service_price_id", "status", "start_at"),
        Index("ix_bookings_customer_start", "customer_id", "start_at"),
        Index("ix_bookings_salon_start", "salon_id", "start_at"),
        Index("ix_bookings_created", "created_at"),
    )

# -------------------------------------------------------------------
# Booking lifecycle audit events
# -------------------------------------------------------------------
class BookingEvent(Base):
    __tablename__ = "booking_events"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(
        String(36),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(80), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    event_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    booking = relationship("Booking", back_populates="events")
    actor = relationship("User")

    __table_args__ = (
        Index("ix_booking_events_booking_created", "booking_id", "created_at"),
        Index("ix_booking_events_booking_type", "booking_id", "event_type"),
    )

# -------------------------------------------------------------------
# Service Reviews
# -------------------------------------------------------------------
class ServiceReview(Base):
    __tablename__ = "service_reviews"

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4())
    )

    booking_id = Column(
        String(36),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one review per booking
        index=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    salon_service_price_id = Column(
        String(36),
        ForeignKey("salon_service_prices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    service_id = Column(
        String(36),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sub_service_id = Column(
        String(36),
        ForeignKey("sub_services.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    stylist_id = Column(
        String(36),
        ForeignKey("salon_stylists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    rating = Column(INTEGER, nullable=False)  # 1–5
    comment = Column(String(1000), nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    booking = relationship(
        "Booking",
        back_populates="review",
    )
    user = relationship(
        "User",
        back_populates="service_reviews",
    )
    salon = relationship(
        "Salon",
        back_populates="service_reviews",
    )
    stylist = relationship(
        "SalonStylist",
        back_populates="reviews",
    )
    salon_service_price = relationship(
        "SalonServicePrice",
        back_populates="reviews",
    )
    service = relationship("Services")
    sub_service = relationship("SubServices")
    
    Index("ix_review_service", "salon_service_price_id")
    Index("ix_review_salon", "salon_id")
    Index("ix_review_stylist", "stylist_id")
