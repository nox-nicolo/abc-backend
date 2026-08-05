"""Provides the Salon Config Service request and response schema module for profile workflows."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from core.enumeration import ServiceCreatedStatus


class SalonServiceSelectableItem(BaseModel):
    service_id: str
    service_name: str
    service_image: Optional[str] = None

    sub_service_id: Optional[str] = None
    sub_service_name: Optional[str] = None

    is_configured: bool
    salon_service_price_id: Optional[str] = None
    status: Optional[ServiceCreatedStatus] = None

    class Config:
        from_attributes = True


class SalonServiceSelectableList(BaseModel):
    items: List[SalonServiceSelectableItem]


class SalonServiceBenefitIn(BaseModel):
    benefit: str
    position: int


class SalonServiceProductIn(BaseModel):
    product_name: str
    brand: Optional[str] = None

class SalonServiceConfigStylistOut(BaseModel):
    id: str
    name: str
    image: Optional[str] = None

    class Config:
        from_attributes = True

class SalonServiceConfigIn(BaseModel):
    service_id: Optional[str] = None
    sub_service_id: Optional[str] = None

    price_min: Optional[int] = None
    price_max: Optional[int] = None
    currency: str = "TZS"

    duration_minutes: Optional[int] = None
    concurrent_capacity: int = Field(default=1, ge=1)

    status: ServiceCreatedStatus

    stylist_ids: List[str] = Field(default_factory=list)
    benefits: List[SalonServiceBenefitIn] = Field(default_factory=list)
    products: List[SalonServiceProductIn] = Field(default_factory=list)


class SalonServiceConfigOut(BaseModel):
    id: str

    service_id: Optional[str]
    sub_service_id: Optional[str]

    price_min: Optional[int]
    price_max: Optional[int]
    currency: str

    duration_minutes: Optional[int]
    concurrent_capacity: int = 1

    status: ServiceCreatedStatus
    created_at: datetime

    stylists: List[SalonServiceConfigStylistOut]

    benefits: List[SalonServiceBenefitIn]
    products: List[SalonServiceProductIn]

    class Config:
        from_attributes = True
