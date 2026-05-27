from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class NotificationActor(BaseModel):
    id: str
    username: str
    profile_picture: Optional[str] = None
    role: Optional[str] = None
    salon_id: Optional[str] = None


class NotificationItem(BaseModel):
    id: str
    # "like" | "comment" | "reply"
    # | "booking_new" | "booking_confirmed" | "booking_rejected"
    # | "booking_cancelled" | "booking_completed" | "booking_rescheduled"
    # | "booking_reminder_ai"
    type: str
    actor: NotificationActor
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    booking_id: Optional[str] = None
    # short snippet used for comment/reply types
    preview: Optional[str] = None
    is_grouped: bool = False
    group_count: int = 1
    is_read: bool
    delivery_status: Literal["created", "scheduled", "sent", "failed", "read"] = "sent"
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    next_cursor: Optional[str] = None


class UnreadCountResponse(BaseModel):
    unread: int


class SalonEventCampaignRequest(BaseModel):
    upcoming_event: str = Field(..., min_length=2, max_length=80)
    days_until_event: int = Field(..., ge=0, le=21)
    service_type: str = Field(..., min_length=2, max_length=80)
    target_group: Literal["followers", "past_customers", "all_engaged"]
    booking_link: Optional[str] = Field(None, max_length=500)
    stylist_name: Optional[str] = Field(None, max_length=80)
    max_recipients: int = Field(500, ge=1, le=2000)


class SalonEventCampaignResponse(BaseModel):
    channel: str
    trigger: str
    target_group: str
    recipients_found: int
    sent: int
    skipped_duplicates: int
    sample_message: Optional[str] = None


class SalonPromotionCampaignRequest(BaseModel):
    offer_title: str = Field(..., min_length=2, max_length=100)
    service_type: str = Field(..., min_length=2, max_length=80)
    target_group: Literal["followers", "past_customers", "all_engaged"]
    discount_code: Optional[str] = Field(None, max_length=40)
    expires_at: Optional[str] = Field(None, max_length=40)
    booking_link: Optional[str] = Field(None, max_length=500)
    stylist_name: Optional[str] = Field(None, max_length=80)
    max_recipients: int = Field(500, ge=1, le=2000)


class SalonPromotionCampaignResponse(BaseModel):
    channel: str
    trigger: str
    target_group: str
    recipients_found: int
    sent: int
    skipped_duplicates: int
    sample_message: Optional[str] = None
