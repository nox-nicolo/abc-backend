from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class AvailabilityOverrideIn(BaseModel):
    date: date
    is_closed: bool = False
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    reason: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_times(self):
        if not self.is_closed:
            if not self.open_time or not self.close_time:
                raise ValueError("open_time and close_time are required unless closed")
            if self.close_time <= self.open_time:
                raise ValueError("close_time must be after open_time")
        return self


class AvailabilityOverrideOut(AvailabilityOverrideIn):
    id: str

    class Config:
        from_attributes = True


class AvailabilitySlot(BaseModel):
    start_at: datetime
    end_at: datetime
    remaining_capacity: int


class AvailabilitySlotsResponse(BaseModel):
    date: date
    salon_service_price_id: str
    is_open: bool
    reason: Optional[str] = None
    slots: List[AvailabilitySlot]
