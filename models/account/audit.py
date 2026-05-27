import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import relationship

from models.base import Base


class UserAuditEvent(Base):
    __tablename__ = "user_audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(80), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(String(500), nullable=True)
    event_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = relationship("User")

    __table_args__ = (
        Index("ix_user_audit_events_user_created", "user_id", "created_at"),
    )
