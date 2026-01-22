from datetime import datetime
import uuid
from sqlalchemy import TEXT, Column, Integer, ForeignKey, String, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from core.enumeration import Status
from models.base import Base  

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, index=True)  # Use Integer for auto-incrementing ID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    via = Column(String(20), nullable=False)  # Specify possible verification methods (e.g., 'email', 'phone')
    code = Column(String(128), nullable=False)  # Consider length for different verification code types
    token = Column(String(255), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))  # Unique token
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration for codes
    phone_verified = Column(Boolean, default=False)
    status = Column(Enum(Status), default=Status.PENDING, nullable=False)
    

    # Relationship with User table (one-to-one)
    user = relationship("User", back_populates="verification")  # One-to-one relationship with User

    def __repr__(self):
        return f"<Verification {self.code} (user_id: {self.user_id}, token: {self.token})>"