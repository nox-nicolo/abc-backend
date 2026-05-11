import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship

from models.base import Base


class UserDeviceToken(Base):
    __tablename__ = "user_device_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(120), nullable=False)
    platform = Column(String(30), nullable=False)
    push_provider = Column(String(30), nullable=False, default="fcm")
    push_token = Column(String(512), nullable=False)
    app_version = Column(String(80), nullable=True)
    build_number = Column(String(80), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_device_tokens_user_device"),
        Index("ix_user_device_tokens_user_active", "user_id", "is_active"),
        Index("ix_user_device_tokens_token", "push_token"),
    )
