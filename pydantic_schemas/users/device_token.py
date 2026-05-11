from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DeviceTokenUpsert(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=120)
    platform: Literal["android", "ios", "web", "macos", "windows", "linux", "unknown"]
    push_token: str = Field(..., min_length=20, max_length=512)
    push_provider: Literal["fcm"] = "fcm"
    app_version: Optional[str] = Field(None, max_length=80)
    build_number: Optional[str] = Field(None, max_length=80)


class DeviceTokenResponse(BaseModel):
    id: str
    device_id: str
    platform: str
    push_provider: str
    is_active: bool
    last_seen_at: datetime


class DeviceTokenListResponse(BaseModel):
    items: list[DeviceTokenResponse]
