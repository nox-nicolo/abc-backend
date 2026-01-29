from datetime import datetime, timezone
from sqlalchemy import BOOLEAN, FLOAT, TIME, Column, ForeignKey, Index, String, DateTime, INTEGER, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base
from sqlalchemy import Column, String, DateTime, ForeignKey, FLOAT
from sqlalchemy.orm import relationship
from datetime import datetime, timezone



# -------------------------------------------------------------------
# Salon Profile 
# -------------------------------------------------------------------
class Salon(Base):
    __tablename__ = "salons"

    id = Column(String(36), primary_key=True, index=True)

    # Business identity
    title = Column(String(200), nullable=False)
    slogan = Column(String(300), nullable=True)
    description = Column(String(1000), nullable=True)
    display_ads = Column(String(200), nullable=True)

    # System
    profile_completion = Column(FLOAT, default=0.0, nullable=False)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ───────────── Relationships ─────────────
    user = relationship("User", back_populates="salon")

    contacts = relationship("SalonContact", back_populates="salon", cascade="all, delete-orphan")
    galleries = relationship("SalonGallery", back_populates="salon", cascade="all, delete-orphan")
    rated = relationship("Rate", back_populates="salon", cascade="all, delete-orphan")
    salon_service_prices = relationship("SalonServicePrice", back_populates="salon", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="salon", cascade="all, delete-orphan")
    working_hours = relationship("SalonWorkingHour", back_populates="salon", cascade="all, delete-orphan",)
    location = relationship("SalonLocation", back_populates="salon", cascade="all, delete-orphan", uselist=False,)   # one-to-one
    stylists = relationship("SalonStylist", back_populates="salon", cascade="all, delete-orphan",)
    service_reviews = relationship("ServiceReview", back_populates="salon", cascade="all, delete-orphan",)
    sponsored = relationship("SponsoredSalon", back_populates="salon", uselist=False, cascade="all, delete-orphan",)
    followers = relationship("SalonFollower", back_populates="salon", cascade="all, delete-orphan",)
    blocked_by = relationship("SalonBlock", back_populates="salon", cascade="all, delete-orphan",)
    reports = relationship("SalonReport", back_populates="salon", cascade="all, delete-orphan",)


#                               END
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Visuals/Gallery
# -------------------------------------------------------------------
class SalonGallery(Base):
    __tablename__ = "salon_galleries"

    id = Column(String(36), primary_key=True, index=True)
# -------------------------------------------------------------------
    salon_id = Column(String(36), ForeignKey("salons.id", onupdate="CASCADE",  ondelete="CASCADE"), nullable=False,)
    file_name = Column(String(200), nullable=False)

    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    salon = relationship("Salon", back_populates="galleries")
    
#                               END
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Followers
# -------------------------------------------------------------------

# class Followers(Base):
#     __tablename__ = "followers"

#     id = Column(String(36), primary_key=True)
#     follower = Column(String(36), ForeignKey("users.id"), nullable=False)
#     follow_this = Column(String(36), ForeignKey("users.id"), nullable=False)
#     created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

#     # Relationships (EXPLICIT foreign_keys)
#     follower_user = relationship("User", foreign_keys=[follower], back_populates="following")
#     follow_this_user = relationship("User", foreign_keys=[follow_this], back_populates="follow")
    
#     __table_args__ = (
#         UniqueConstraint("follower", "follow_this", name="uq_unique_follow"),
#     )


#                               END
# ------------------------------------------------------------------- 


# -------------------------------------------------------------------
# Rated
# -------------------------------------------------------------------
class Rate(Base):
    __tablename__ = "rated"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=False)
    value = Column(INTEGER, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="rated")
    salon = relationship("Salon", back_populates="rated")
    __table_args__ = (
        UniqueConstraint("user_id", "salon_id", name="uq_user_salon_rating"),
    )
    
    
#                               END
# ------------------------------------------------------------------- 


# -------------------------------------------------------------------
# Salon Service Price
# -------------------------------------------------------------------
class SalonServicePrice(Base):
    __tablename__ = "salon_service_prices"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(String(36), ForeignKey("services.id", ondelete="CASCADE"), nullable=True)
    sub_service_id = Column(String(36), ForeignKey("sub_services.id", ondelete="CASCADE"), nullable=True)

    price_min = Column(INTEGER, nullable=True)
    price_max = Column(INTEGER, nullable=True)

    currency = Column(String(10), default="TZS")
    duration_minutes = Column(INTEGER, nullable=True)

    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    salon = relationship("Salon", back_populates="salon_service_prices")
    service = relationship("Services", back_populates="salon_service_prices")
    sub_service = relationship("SubServices", back_populates="salon_service_prices")
    bookings = relationship("Booking", back_populates="salon_service_price")
    benefits = relationship("SalonServiceBenefit", back_populates="salon_service_price", cascade="all, delete-orphan", order_by="SalonServiceBenefit.position")
    products = relationship("SalonServiceProduct", back_populates="salon_service_price", cascade="all, delete-orphan")
    reviews = relationship("ServiceReview", back_populates="salon_service_price", cascade="all, delete-orphan", )

    Index("ix_service_lookup", "salon_id", "service_id", "sub_service_id")

    
#                               END
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Service Benefits
# -------------------------------------------------------------------
class SalonServiceBenefit(Base):
    __tablename__ = "salon_service_benefits"

    id = Column(String(36), primary_key=True, index=True)

    salon_service_price_id = Column(
        String(36),
        ForeignKey("salon_service_prices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    benefit = Column(String(500), nullable=False)

    position = Column(INTEGER, default=0, nullable=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    salon_service_price = relationship(
        "SalonServicePrice",
        back_populates="benefits",
    )


#                               END
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Service Products / Tools
# -------------------------------------------------------------------
class SalonServiceProduct(Base):
    __tablename__ = "salon_service_products"

    id = Column(String(36), primary_key=True, index=True)

    salon_service_price_id = Column(
        String(36),
        ForeignKey("salon_service_prices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_name = Column(String(255), nullable=False)
    brand = Column(String(255), nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    salon_service_price = relationship(
        "SalonServicePrice",
        back_populates="products",
    )


#                               END
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Stylists
# -------------------------------------------------------------------
class SalonStylist(Base):
    __tablename__ = "salon_stylists"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(100), nullable=True)   # e.g. Senior Stylist, Nail Tech
    bio = Column(String(500), nullable=True)

    is_owner = Column(BOOLEAN, default=False, nullable=False)
    is_active = Column(BOOLEAN, default=True, nullable=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    services = relationship("StylistService", back_populates="stylist",  cascade="all, delete-orphan",)
    salon = relationship("Salon", back_populates="stylists")
    user = relationship("User", back_populates="stylist_profile")
    rating = relationship(
        "StylistRating",
        back_populates="stylistRating",
        cascade="all, delete-orphan",
    )
    reviews = relationship(
        "ServiceReview",
        back_populates="stylist",
    )

    __table_args__ = (
        UniqueConstraint("salon_id", "user_id", name="uq_salon_stylist"),
    )


#                               END
# -------------------------------------------------------------------



# -------------------------------------------------------------------
# Stylist Services
# -------------------------------------------------------------------
class StylistService(Base):
    __tablename__ = "stylist_services"

    id = Column(String(36), primary_key=True, index=True)

    stylist_id = Column(
        String(36),
        ForeignKey("salon_stylists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    salon_service_price_id = Column(
        String(36),
        ForeignKey("salon_service_prices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    stylist = relationship("SalonStylist", back_populates="services")
    salon_service_price = relationship("SalonServicePrice")

    __table_args__ = (
        UniqueConstraint(
            "stylist_id",
            "salon_service_price_id",
            name="uq_stylist_service",
        ),
    )


#                               END
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Stylist Rating
# -------------------------------------------------------------------
class StylistRating(Base):
    __tablename__ = "stylist_ratings"

    id = Column(String(36), primary_key=True, index=True)

    stylist_id = Column(
        String(36),
        ForeignKey("salon_stylists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    value = Column(INTEGER, nullable=False)  # e.g. 1–5
    comment = Column(String(500), nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    stylistRating = relationship("SalonStylist", back_populates="rating")

    __table_args__ = (
        UniqueConstraint("stylist_id", "user_id", name="uq_user_stylist_rating"),
    )


#                               END
# -------------------------------------------------------------------


class SalonContact(Base):
    __tablename__ = "salon_contacts"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type = Column(String(30), nullable=False)
    value = Column(String(255), nullable=False)

    is_primary = Column(BOOLEAN, default=False, nullable=False)
    is_verified = Column(BOOLEAN, default=False, nullable=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    salon = relationship("Salon", back_populates="contacts")
    
    __table_args__ = (
        Index(
            "uq_primary_contact_per_type",
            "salon_id",
            "type",
            unique=True,
            postgresql_where=(is_primary == True),
        ),
    )



class SalonWorkingHour(Base):
    __tablename__ = "salon_working_hours"

    id = Column(String(36), primary_key=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day_of_week = Column(INTEGER, nullable=False)
    # 0 = Monday, 6 = Sunday (ISO / Python compatible)

    is_open = Column(BOOLEAN, default=False, nullable=False)

    open_time = Column(TIME, nullable=True)
    close_time = Column(TIME, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    salon = relationship("Salon", back_populates="working_hours")
    
    __table_args__ = (
        UniqueConstraint("salon_id", "day_of_week", name="uq_salon_day"),
    )





class SalonLocation(Base):
    __tablename__ = "salon_locations"

    id = Column(String(36), primary_key=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one location per salon
        index=True,
    )

    # Structured address
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)   # optional
    street = Column(String(200), nullable=True)

    # Coordinates (map-ready)
    latitude = Column(FLOAT, nullable=True)
    longitude = Column(FLOAT, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    salon = relationship("Salon", back_populates="location")




# -------------------------------------------------------------------
# Sponsored Salons (Global Marketing)
# -------------------------------------------------------------------
class SponsoredSalon(Base):
    __tablename__ = "sponsored_salons"
    id = Column(String(36), primary_key=True, index=True)
    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # billing_subscription_id = Column(String(36), ForeignKey("billing_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True,)
    plan_type = Column(String(50), nullable=False, default="basic", index=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(BOOLEAN, default=True, nullable=False, index=True)
    priority = Column(INTEGER, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    salon = relationship(
        "Salon",
        back_populates="sponsored",)
    
    __table_args__ = (Index("ix_active_sponsored_salon", "plan_type", "is_active", "start_at", "end_at"),)


#                               END
# -------------------------------------------------------------------

# Editted later

class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)  # active, cancelled, expired

    provider = Column(String(50), nullable=True)  # stripe, flutterwave, etc
    provider_ref = Column(String(100), nullable=True)

    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SalonFollower(Base):
    __tablename__ = "salon_followers"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notifications_enabled = Column(BOOLEAN, default=True, nullable=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ───────────── Relationships ─────────────
    salon = relationship(
        "Salon",
        back_populates="followers",
    )

    user = relationship(
        "User",
        back_populates="followed_salons",
    )

    __table_args__ = (
        UniqueConstraint("salon_id", "user_id", name="uq_salon_user_follow"),
    )


class SalonBlock(Base):
    __tablename__ = "salon_blocks"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    salon = relationship(
        "Salon",
        back_populates="blocked_by",
    )

    user = relationship(
        "User",
        back_populates="blocked_salons",
    )

    __table_args__ = (
        UniqueConstraint("salon_id", "user_id", name="uq_user_block_salon"),
    )


class SalonReport(Base):
    __tablename__ = "salon_reports"

    id = Column(String(36), primary_key=True, index=True)

    salon_id = Column(
        String(36),
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reason = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    salon = relationship("Salon", back_populates="reports")
    user = relationship("User", back_populates="salon_reports")

    __table_args__ = (
        UniqueConstraint("salon_id", "user_id", name="uq_user_report_salon"),
    )
