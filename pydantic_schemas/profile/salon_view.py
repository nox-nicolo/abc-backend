from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel



class SalonCoreSchema(BaseModel):
    id: str
    username: str
    name: str
    slogan: Optional[str]
    description: Optional[str]
    profile_picture: Optional[str]
    cover_image: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True



class SalonViewerSchema(BaseModel):
    is_following: bool
    notifications_enabled: bool
    is_blocked: bool


class SalonMetricsSchema(BaseModel):
    followers_count: int
    posts_count: int
    rating: float
    reviews_count: int



class SalonTodayAvailabilitySchema(BaseModel):
    day: int
    open_time: Optional[str]
    close_time: Optional[str]


class SalonWeeklyAvailabilitySchema(BaseModel):
    day: int
    is_open: bool
    open: Optional[str] = None
    close: Optional[str] = None



class SalonAvailabilitySchema(BaseModel):
    is_open_now: bool
    today: Optional[SalonTodayAvailabilitySchema]
    weekly: List[SalonWeeklyAvailabilitySchema]



class SalonLocationSchema(BaseModel):
    address: Optional[str]
    lat: Optional[float]
    lng: Optional[float]



class SalonContactsSchema(BaseModel):
    phone: Optional[str]
    sms: Optional[str]
    whatsapp: Optional[str]
    email: Optional[str]
    location: Optional[SalonLocationSchema]



class SalonGalleryItemSchema(BaseModel):
    id: str
    image_url: str
    order: int


class SalonMediaSchema(BaseModel):
    gallery: List[SalonGalleryItemSchema]


class SalonActionsSchema(BaseModel):
    can_follow: bool
    can_unfollow: bool
    can_contact: bool
    can_share: bool
    can_report: bool
    can_block: bool




# Pydantinc schemas for User view profile response

class SalonFollowerItemSchema(BaseModel):
    user_id: str
    username: str
    name: str
    avatar: Optional[str]
    is_following: bool


class SalonFollowersResponseSchema(BaseModel):
    count: int
    items: List[SalonFollowerItemSchema]
    next_cursor: Optional[str]


class SalonServiceStylistSchema(BaseModel):
    id: str
    name: str
    avatar: Optional[str]

    class Config:
        from_attributes = True


class SalonServiceItemSchema(BaseModel):
    id: str

    category_id: Optional[str]
    category_name: Optional[str]

    sub_service_id: Optional[str]
    name: Optional[str]

    image: Optional[str]

    price_min: Optional[int]
    price_max: Optional[int]
    currency: str

    duration_minutes: Optional[int]

    stylists: List[SalonServiceStylistSchema]

    class Config:
        from_attributes = True


class SalonServiceCategorySchema(BaseModel):
    category_id: str
    category_name: str
    services: List[SalonServiceItemSchema]


class SalonServicesSchema(BaseModel):
    categories: List[SalonServiceCategorySchema]



class SalonViewProfileResponseSchema(BaseModel):
    salon: SalonCoreSchema
    viewer: SalonViewerSchema
    metrics: SalonMetricsSchema
    availability: SalonAvailabilitySchema
    contacts: SalonContactsSchema
    media: SalonMediaSchema
    actions: SalonActionsSchema
    services: SalonServicesSchema

