import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    INTEGER, Column, DateTime, Index, String, ForeignKey, Enum, TIMESTAMP,
    Integer, Numeric, Text
)
from sqlalchemy.orm import relationship

from core.enumeration import BookingStatus
from models.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    customer_id = Column( String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,  index=True)

    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)

    salon_service_price_id = Column(String(36), ForeignKey("salon_service_prices.id", ondelete="SET NULL"), nullable=True, index=True)

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
    review = relationship(
        "ServiceReview",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def customer_name(self):
        return self.customer.name if self.customer else None
    
    
    
    
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
    
    Index("ix_review_service", "salon_service_price_id")
    Index("ix_review_salon", "salon_id")
    Index("ix_review_stylist", "stylist_id")

