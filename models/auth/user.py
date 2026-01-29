from datetime import datetime, timezone
from sqlalchemy import Column, Enum, ForeignKey, LargeBinary, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from core.enumeration import AccountAccessStatus
from models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password = Column(LargeBinary, nullable=False)

    role = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    account_access = Column(
        Enum(AccountAccessStatus),
        default=AccountAccessStatus.PENDING,
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    verification = relationship("Verification", back_populates="user", uselist=False, cascade="all, delete-orphan")
    profile_picture = relationship(
        "ProfilePicture",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    select_service = relationship("UserSelectServices", back_populates="user", uselist=False, cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="user")
    comments = relationship("PostComment", back_populates="user", cascade="all, delete-orphan")
    shared_posts = relationship("PostShare", back_populates="share_user", foreign_keys="PostShare.share_user_id", cascade="all, delete-orphan")
    received_shared_posts = relationship("PostShare", back_populates="user", foreign_keys="PostShare.user_id", cascade="all, delete-orphan")
    reports = relationship("PostReport", back_populates="user", cascade="all, delete-orphan")
    views = relationship("PostView", back_populates="user", cascade="all, delete-orphan")
    mentions = relationship("PostMention", back_populates="mentioned_user", cascade="all, delete-orphan")
    bookmarks = relationship("PostBoorkmark", back_populates="user", cascade="all, delete-orphan")
    salon = relationship("Salon", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # following = relationship("Followers", back_populates="follower_user", foreign_keys="Followers.follower", cascade="all, delete-orphan")
    # follow = relationship("Followers", back_populates="follow_this_user", foreign_keys="Followers.follow_this", cascade="all, delete-orphan")
    search_histories = relationship("SearchHistory",back_populates="history_user",cascade="all, delete-orphan",)
    bookings = relationship("Booking", back_populates="customer",cascade="all, delete-orphan",)
    rated = relationship("Rate", back_populates="user", cascade="all, delete-orphan")
    stylist_profile = relationship("SalonStylist",  back_populates="user", uselist=False,)
    service_reviews = relationship("ServiceReview", back_populates="user", cascade="all, delete-orphan",)
    followed_salons = relationship("SalonFollower", back_populates="user", cascade="all, delete-orphan",)
    blocked_salons = relationship("SalonBlock", back_populates="user", cascade="all, delete-orphan",)
    salon_reports = relationship("SalonReport", back_populates="user", cascade="all, delete-orphan",)

    
    def __repr__(self):
        return f"<User id={self.id}, username={self.username}, email={self.email}, account_access={self.account_access}>"


