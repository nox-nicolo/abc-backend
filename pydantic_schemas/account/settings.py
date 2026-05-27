from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountSettingsResponse(BaseModel):
    settings: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class AccountSettingsUpdate(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
