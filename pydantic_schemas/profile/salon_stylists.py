# app/schemas/salon_stylist.py

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


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
    salon_id: str
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
class StylistUserMini(BaseModel):
    """
    Minimal user payload to show in stylist responses.
    Adjust fields to match your User model.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: Optional[str] = None
    name: Optional[str] = None
    profile_picture: Optional[str] = None


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
