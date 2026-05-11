from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


# Allowed lead-time presets (minutes). Keep this aligned with the
# frontend dropdown so we don't accept arbitrary values.
ALLOWED_LEAD_MINUTES = {5, 15, 30, 60, 120}


class NotificationPreferenceResponse(BaseModel):
    allow_likes: bool
    allow_comments: bool
    allow_bookings: bool
    allow_promotions: bool
    allow_reminders: bool
    reminder_lead_minutes: int

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    allow_likes: Optional[bool] = None
    allow_comments: Optional[bool] = None
    allow_bookings: Optional[bool] = None
    allow_promotions: Optional[bool] = None
    allow_reminders: Optional[bool] = None
    reminder_lead_minutes: Optional[int] = Field(
        default=None,
        description="Minutes before booking start to fire the reminder.",
    )
