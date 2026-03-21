from typing import Optional
from pydantic import BaseModel, ConfigDict


class MajorServiceDetails(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    rating: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class MinorServiceItem(BaseModel):
    id: str
    service_id: str
    name: str
    image: Optional[str] = None
    rating: Optional[float] = None
    is_event: bool = False

    model_config = ConfigDict(from_attributes=True)


class SalonServiceDetailsItem(BaseModel):
    salon_id: str
    salon_name: str
    salon_image: Optional[str] = None
    salon_city: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    currency: Optional[str] = None
    duration_minutes: Optional[int] = None
    rating: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceDetailsResponse(BaseModel):
    major_service: MajorServiceDetails
    minor_service: Optional[MinorServiceItem] = None
    minor_services: Optional[list[MinorServiceItem]] = None
    salon_details: list[SalonServiceDetailsItem]

    model_config = ConfigDict(from_attributes=True)