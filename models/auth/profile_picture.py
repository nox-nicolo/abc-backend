from sqlalchemy import TEXT, Column, Boolean, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base 

class ProfilePicture(Base):
    # Table name
    __tablename__ = "profile_pictures"

    # Columns
    id = Column(String(36), primary_key=True, index=True)  # Unique identifier for the profile picture
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)  # Foreign key to User table
    file_name = Column(String(255), nullable=False)  # Name of the file
    is_custom = Column(Boolean, nullable=False, default=False)  # custom or default image
    uploaded_at = Column(DateTime, nullable=False)  # Timestamp of when the image was uploaded
    updated_at = Column(DateTime, nullable=True)  # Timestamp of when the image was last updated

    # Relationship (ONE profile picture ↔ ONE user)
    user = relationship(
        "User",
        back_populates="profile_picture",
        uselist=False,
    )

