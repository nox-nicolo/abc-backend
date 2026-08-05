"""Provides the Choose Salon request and response schema module for booking workflows."""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from pydantic_schemas.pagination import PaginationMeta


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
    pagination: PaginationMeta


class BookingStylistOption(BaseModel):
    stylist_id: str
    user_id: str
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    image: Optional[str] = None
    rating: float = 0.0
    reviews_count: int = 0
    is_recommended: bool = False
    recommendation_reason: Optional[str] = None


class BookingStylistOptionListResponse(BaseModel):
    results: List[BookingStylistOption]
    pagination: PaginationMeta
