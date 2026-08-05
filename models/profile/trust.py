"""Provides the Trust database model module for profile workflows."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String

from models.base import Base


class SalonBusinessDocument(Base):
    __tablename__ = "salon_business_documents"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    document_type = Column(String(60), nullable=False, default="business_document")
    file_name = Column(String(255), nullable=False)
    review_status = Column(String(30), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_salon_business_documents_salon_status", "salon_id", "review_status"),
    )
