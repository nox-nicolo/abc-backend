"""Provides the Salon Activity request and response schema module for profile workflows."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ActivityActorSchema(BaseModel):
    id: str
    username: str
    name: str
    profile_picture: Optional[str] = None


class ActivityItemSchema(BaseModel):
    """Single activity event.

    type values:
      - booking_new        (someone booked your service)
      - booking_completed  (a booking was completed)
      - booking_cancelled  (a booking was cancelled)
      - follower_new       (someone followed your salon)
      - review_new         (someone left a review)
      - post_like          (someone liked your post)
    """
    id: str
    type: str
    message: str
    actor: Optional[ActivityActorSchema] = None
    created_at: datetime
    # optional context ids for deep-linking
    ref_id: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityFeedResponse(BaseModel):
    items: List[ActivityItemSchema]
    next_cursor: Optional[str] = None
