from datetime import datetime
from pydantic import AliasChoices, BaseModel, Field, ConfigDict
from typing import Optional
from core.enumeration import BookingStatus


# -------------------------------------------------
# Create booking
# -------------------------------------------------

class BookingCreate(BaseModel):
    # 🔑 CHANGED: concrete bookable offering
    salon_service_price_id: str

    start_at: datetime = Field(..., description="Requested start time (UTC)")
    note: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------
# Booking response
# -------------------------------------------------

class BookingResponse(BaseModel):
    id: str

    customer_id: str
    customer_name: Optional[str] = None
    salon_id: str

    # ❌ REMOVED: sub_service_id
    # sub_service_id: Optional[str]

    status: BookingStatus

    start_at: datetime
    end_at: datetime

    # 🔒 snapshots (agreement)
    service_name_snapshot: Optional[str]
    price_snapshot: float
    currency_snapshot: str
    duration_minutes_snapshot: int

    note: Optional[str]
    
    cancel_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------
# Status update (unchanged)
# -------------------------------------------------

class BookingStatusUpdate(BaseModel):
    status: BookingStatus

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------
# Cancel booking (unchanged)
# -------------------------------------------------

class BookingCancel(BaseModel):
    reason: Optional[str] = Field(None, max_length=255)


# -------------------------------------------------
# Booking list item (minor change)
# -------------------------------------------------

class BookingListItem(BaseModel):
    id: str
    status: BookingStatus

    start_at: datetime
    end_at: datetime

    service_name_snapshot: Optional[str]
    price_snapshot: float
    currency_snapshot: str
    
    cancel_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
