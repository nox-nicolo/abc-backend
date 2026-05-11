import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship

from models.base import Base


class UserMute(Base):
    __tablename__ = "user_mutes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(20), nullable=False, index=True)
    target_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_mute_target"),
        Index("ix_user_mutes_user_type_created", "user_id", "target_type", "created_at"),
    )
