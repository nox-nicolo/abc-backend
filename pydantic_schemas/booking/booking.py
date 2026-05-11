from datetime import date, datetime
from pydantic import AliasChoices, BaseModel, Field, ConfigDict
from typing import List, Optional
from core.enumeration import BookingStatus
from pydantic_schemas.pagination import Page


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

    has_review: bool = False
    review_rating: Optional[int] = None
    review_comment: Optional[str] = None
    review_created_at: Optional[datetime] = None

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
# Reschedule booking
# -------------------------------------------------

class BookingReschedule(BaseModel):
    start_at: datetime = Field(..., description="New requested start time (UTC)")


# -------------------------------------------------
# Review booking
# -------------------------------------------------

class BookingReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class BookingReviewResponse(BaseModel):
    id: str
    booking_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    has_review: bool = False
    review_rating: Optional[int] = None
    review_comment: Optional[str] = None
    review_created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookingListPage(Page[BookingListItem]):
    pass


class BookingResponsePage(Page[BookingResponse]):
    pass


class AvailabilitySlot(BaseModel):
    start_at: datetime
    end_at: datetime
    remaining_capacity: int


class AvailabilityDay(BaseModel):
    date: date
    is_open: bool
    reason: Optional[str] = None
    slots: List[AvailabilitySlot] = Field(default_factory=list)


class AvailabilityResponse(BaseModel):
    items: List[AvailabilityDay]
