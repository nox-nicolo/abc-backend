"""Provides the Customer Profile database model module for auth workflows."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    bio = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)  # male, female, other, prefer_not_to_say

    updated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="customer_profile", uselist=False)
