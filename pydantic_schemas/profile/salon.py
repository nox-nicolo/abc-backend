import datetime
from typing import Optional
from pydantic import BaseModel


class SalonContactResponse(BaseModel):
    id: str
    type: str        # phone, email, instagram, website, etc
    value: str
    is_primary: bool
    is_verified: bool

    class Config:
        from_attributes = True


class SalonLocationResponse(BaseModel):
    country: Optional[str]
    city: Optional[str]
    region: Optional[str]
    street: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True


class SalonWorkingHourResponse(BaseModel):
    day_of_week: int          # 0 = Monday .. 6 = Sunday
    is_open: bool
    open_time: Optional[datetime.time]
    close_time: Optional[datetime.time]

    class Config:
        from_attributes = True


class SalonGalleryResponse(BaseModel):
    id: str
    file_name: str
    image_url: Optional[str] = None # New field

    class Config:
        from_attributes = True


from typing import List, Optional
from pydantic import BaseModel


class SalonProfileResponse(BaseModel):
    # Core identity
    id: str
    username: str
    title: str
    slogan: Optional[str]
    description: Optional[str]
    displayAds: Optional[str]
    profileCompletion: float

    # Media
    profilePicture: Optional[str]

    # Aggregates (normalized)
    location: Optional[SalonLocationResponse]
    contacts: List[SalonContactResponse]
    workingHours: List[SalonWorkingHourResponse]
    gallery: List[SalonGalleryResponse]

    # Meta
    followers: int
    rated: Optional[float]

    class Config:
        from_attributes = True
