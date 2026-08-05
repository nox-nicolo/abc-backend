"""Provides the Salon Stylists request and response schema module for profile workflows."""

# app/schemas/salon_stylist.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, List

from pydantic import BaseModel, Field, ConfigDict, computed_field

from core.enumeration import ImageURL

from core.enumeration import ImageURL


# -----------------------------
# Core (shared) fields
# -----------------------------
class SalonStylistBase(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)

    is_owner: bool = False
    is_active: bool = True


# -----------------------------
# Create
# -----------------------------
class SalonStylistCreate(SalonStylistBase):
    """
    Creating a stylist record for a salon.
    You can either:
      - attach an existing user via user_id (recommended), OR
      - later extend this to invite/create a user account flow.
    """
    # salon_id: str
    user_id: str


# -----------------------------
# Update (PATCH)
# -----------------------------
class SalonStylistUpdate(BaseModel):
    """
    Partial update (PATCH). Everything optional.
    """
    title: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)

    is_owner: Optional[bool] = None
    is_active: Optional[bool] = None


# -----------------------------
# Output models
# -----------------------------
# Create a small schema for the picture itself
class ProfilePictureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    file_name: str  # Ensure this matches your DB column name

class StylistUserMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: Optional[str] = None
    name: Optional[str] = None

    # Replace Any with your new schema
    profile_picture: Optional[ProfilePictureOut] = None

    @computed_field
    @property
    def profile_picture_url(self) -> Optional[str]:
        # Now 'self.profile_picture' is a Pydantic object, not a raw DB model
        if not self.profile_picture or not self.profile_picture.file_name:
            return None

        return f"{ImageURL.PROFILE_URL.value}/{self.profile_picture.file_name}"
    

class SalonStylistOutSimple(BaseModel):
    message: str = "Stylist created successfully"


class SalonStylistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    salon_id: str
    user_id: str

    title: Optional[str] = None
    bio: Optional[str] = None

    is_owner: bool
    is_active: bool

    created_at: datetime

    # optional nested user preview
    user: Optional[StylistUserMini] = None


# -----------------------------
# List wrapper (pagination-ready)
# -----------------------------
class SalonStylistListOut(BaseModel):
    items: List[SalonStylistOut]
    total: int
    limit: int
    offset: int


class UserSearchListOut(BaseModel):
    """
    Returns a list of users matching the search criteria
    to be added as stylists.
    """
    items: List[StylistUserMini]
    query: str
    count: int
    
    
# -----------------------------
# Update (PATCH)
# -----------------------------
class SalonStylistUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    is_owner: Optional[bool] = None