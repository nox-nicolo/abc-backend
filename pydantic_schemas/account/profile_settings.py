"""Provides the Profile Settings request and response schema module for account workflows."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CustomerBeautyPreferences(BaseModel):
    styles: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    budget_min: int = Field(default=25000, ge=0)
    budget_max: int = Field(default=150000, ge=0)
    radius_km: int = Field(default=15, ge=1, le=250)
    preferred_area: str = ""


class CustomerRecommendationControls(BaseModel):
    use_saved: bool = True
    use_following: bool = True
    use_bookings: bool = True
    use_location: bool = True
    show_trending: bool = True
    show_promotions: bool = True


class CustomerProfilePreviewVisibility(BaseModel):
    audience: Literal["Anyone with link", "Followers only", "Only me"] = "Anyone with link"
    discoverable: bool = True
    photo: bool = True
    bio: bool = True
    city: bool = True
    following: bool = False
    saved: bool = False
    booking_activity: bool = False


class CustomerBlockedAccounts(BaseModel):
    accounts: list[str] = Field(default_factory=list)


class SalonBookingRules(BaseModel):
    minimum_notice_hours: int = Field(default=4, ge=0, le=336)
    cancel_window_hours: int = Field(default=12, ge=0, le=336)
    slot_interval_minutes: int = Field(default=30, ge=5, le=240)
    buffer_minutes: int = Field(default=15, ge=0, le=240)
    auto_confirm: bool = False
    allow_customer_notes: bool = True


class SalonCampaignDraft(BaseModel):
    id: str | None = None
    title: str
    audience: str = "Followers"
    note: str = ""
    created_at: datetime | None = None


class SalonCampaignDrafts(BaseModel):
    drafts: list[SalonCampaignDraft] = Field(default_factory=list)


class SalonCampaignHistoryItem(BaseModel):
    id: str | None = None
    title: str
    audience: str = "Followers"
    note: str = ""
    status: str = "Sent"
    sent_at: datetime | None = None


class SalonCampaignHistory(BaseModel):
    history: list[SalonCampaignHistoryItem] = Field(default_factory=list)


class SalonTeamPermissions(BaseModel):
    permissions: dict[str, dict[str, bool]] = Field(default_factory=dict)


class AccountDataExport(BaseModel):
    exported_at: datetime
    profile: dict[str, Any] | None = None
    customer_settings: dict[str, Any] = Field(default_factory=dict)
