from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class SalonOfferForBooking(BaseModel):
    # --- identity ---
    salon_service_price_id: str

    # --- salon info ---
    salon_id: str
    salon_name: str
    salon_city: Optional[str] = None
    salon_image: Optional[str] = None  # display_ads / cover image

    # --- style info ---
    sub_service_id: str
    sub_service_name: str

    # --- pricing & duration ---
    price: int
    currency: str
    duration_minutes: int

    # --- optional UX helpers ---
    rated: Optional[float] = None

from typing import List


class SalonOfferListResponse(BaseModel):
    results: List[SalonOfferForBooking]
