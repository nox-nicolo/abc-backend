"""Provides the Notification Preferences request and response schema module for profile workflows."""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional


# Allowed lead-time presets (minutes). Keep this aligned with the
# frontend dropdown so we don't accept arbitrary values.
ALLOWED_LEAD_MINUTES = {5, 15, 30, 60, 120}


class NotificationPreferenceResponse(BaseModel):
    allow_likes: bool
    allow_comments: bool
    allow_bookings: bool
    allow_promotions: bool
    promotions_preferred_time: Optional[str] = None
    allow_reminders: bool
    reminder_lead_minutes: int

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    allow_likes: Optional[bool] = None
    allow_comments: Optional[bool] = None
    allow_bookings: Optional[bool] = None
    allow_promotions: Optional[bool] = None
    promotions_preferred_time: Optional[str] = Field(
        default=None,
        description="Preferred local time for promotion/event notifications, HH:MM.",
    )
    allow_reminders: Optional[bool] = None
    reminder_lead_minutes: Optional[int] = Field(
        default=None,
        description="Minutes before booking start to fire the reminder.",
    )

    @field_validator("promotions_preferred_time")
    @classmethod
    def validate_promotions_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return value
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("promotions_preferred_time must use HH:MM format")
        hour, minute = int(parts[0]), int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("promotions_preferred_time must be a valid time")
        return f"{hour:02d}:{minute:02d}"
