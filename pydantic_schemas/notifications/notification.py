from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class NotificationActor(BaseModel):
    id: str
    username: str
    profile_picture: Optional[str] = None


class NotificationItem(BaseModel):
    id: str
    # "like" | "comment" | "reply"
    # | "booking_new" | "booking_confirmed" | "booking_rejected"
    # | "booking_cancelled" | "booking_completed" | "booking_rescheduled"
    type: str
    actor: NotificationActor
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    booking_id: Optional[str] = None
    # short snippet used for comment/reply types
    preview: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    next_cursor: Optional[str] = None


class UnreadCountResponse(BaseModel):
    unread: int
