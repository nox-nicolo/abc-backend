from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


AdPlacement = Literal["home_feed", "search", "post_view"]
AdMediaType = Literal["image", "video"]
AdStatus = Literal["draft", "active", "paused", "archived"]


class AdCampaignCreate(BaseModel):
    advertiser_name: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=160)
    body: Optional[str] = None
    cta_label: str = Field("Learn more", min_length=1, max_length=40)
    destination_url: HttpUrl
    media_url: HttpUrl
    media_type: AdMediaType = "image"
    placement: AdPlacement
    status: AdStatus = "draft"
    priority: int = Field(0, ge=0, le=100)
    weight: int = Field(1, ge=1, le=100)
    target_country: Optional[str] = None
    target_city: Optional[str] = None
    target_category_id: Optional[str] = None
    target_is_required: bool = False
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    max_impressions: Optional[int] = Field(None, ge=1)
    max_clicks: Optional[int] = Field(None, ge=1)


class AdCampaignOut(BaseModel):
    id: str
    advertiser_name: str
    title: str
    body: Optional[str]
    cta_label: str
    destination_url: str
    media_url: str
    media_type: str
    placement: str
    priority: int
    sponsored_label: str = "Sponsored"


class AdListResponse(BaseModel):
    items: list[AdCampaignOut]


class AdEventRequest(BaseModel):
    placement: AdPlacement
