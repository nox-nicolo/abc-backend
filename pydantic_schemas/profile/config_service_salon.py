from typing import Optional, List
from pydantic import BaseModel


class SalonServiceBenefitOut(BaseModel):
    benefit: str
    position: int

    class Config:
        from_attributes = True


class SalonServiceProductOut(BaseModel):
    product_name: str
    brand: Optional[str] = None

    class Config:
        from_attributes = True


class SalonServiceConfigStylistOut(BaseModel):
    id: str
    name: str
    image: Optional[str] = None

    class Config:
        from_attributes = True


class SalonServiceConfigOut(BaseModel):
    salon_service_price_id: str

    price_min: Optional[int]
    price_max: Optional[int]
    currency: str

    duration_minutes: Optional[int]
    status: str  # active | inactive | archived

    stylists: List[SalonServiceConfigStylistOut]
    # stylists: str

    benefits: List[SalonServiceBenefitOut]
    products: List[SalonServiceProductOut]

    class Config:
        from_attributes = True


class SalonServiceSelectableItem(BaseModel):
    # ---- Service context (ALWAYS PRESENT) ----
    service_id: str
    service_name: str
    service_image: Optional[str] = None

    sub_service_id: Optional[str] = None
    sub_service_name: Optional[str] = None
    sub_service_image: Optional[str] = None

    # ---- Configuration state ----
    is_configured: bool

    # ---- Only present if is_configured == True ----
    config: Optional[SalonServiceConfigOut] = None

    class Config:
        from_attributes = True


# class SalonServiceSelectableResponse(BaseModel):
#     items: SalonServiceSelectableItem


class SalonServiceConfigDetailResponse(BaseModel):
    item: SalonServiceSelectableItem
    
    
from pydantic import BaseModel

class MessageResponse(BaseModel):
    message: str