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


class SalonServiceConfigIn(BaseModel):
    service_id: Optional[str] = None
    sub_service_id: Optional[str] = None

    price_min: Optional[int] = None
    price_max: Optional[int] = None
    currency: str = "TZS"

    duration_minutes: Optional[int] = None

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

    status: ServiceCreatedStatus
    created_at: datetime

    stylist_ids: List[str]

    benefits: List[SalonServiceBenefitIn]
    products: List[SalonServiceProductIn]

    class Config:
        from_attributes = True
