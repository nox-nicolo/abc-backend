from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

MuteTargetType = Literal["salon", "user", "post"]


class MuteResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MuteListResponse(BaseModel):
    items: list[MuteResponse]
