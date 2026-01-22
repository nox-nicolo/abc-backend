from datetime import time
from pydantic import BaseModel, EmailStr, HttpUrl, model_validator
from typing import List, Optional


class AccountMediaResponse(BaseModel):
    profile_picture_url: Optional[str]
    cover_ads_url: Optional[str]
    status: Optional[str]


from pydantic import BaseModel, Field
from typing import Optional


class SalonProfileUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    slogan: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)


class SalonProfileResponse(BaseModel):
    title: Optional[str]
    slogan: Optional[str]
    description: Optional[str]


class SalonContactUpdateRequest(BaseModel):
    phone_numbers: Optional[List[str]] = Field(
        None,
        max_items=3,
        description="Up to 3 phone numbers",
    )
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None

    country: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    street: Optional[str]  = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None



class SalonContactLocationResponse(BaseModel):
    phone_numbers: List[str]
    email: Optional[EmailStr]
    website: Optional[HttpUrl]

    country: Optional[str]
    city: Optional[str]
    street: Optional[str]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]



class WorkingDayRequest(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    is_open: bool
    open_time: Optional[time] = None
    close_time: Optional[time] = None

    @model_validator(mode='after')
    def validate_hours(self):
        if self.is_open:
            if not self.open_time or not self.close_time:
                raise ValueError(f"Day {self.day_of_week}: Times are required when open.")
            if self.close_time <= self.open_time:
                raise ValueError(f"Day {self.day_of_week}: Closing time must be after opening time.")
        return self

class SalonWorkingHoursUpdateRequest(BaseModel):
    # Use 7 as a strict requirement to ensure all days are covered in one sync
    working_days: List[WorkingDayRequest] = Field(..., min_length=7, max_length=7)

class SalonWorkingHoursResponse(BaseModel):
    working_days: List[WorkingDayRequest]
    


class SalonGalleryResponse(BaseModel):
    id: str
    file_name: str
    # Add a full URL field for the Flutter app to display images easily
    image_url: Optional[str] = None 

    class Config:
        from_attributes = True

class GalleryUpdatePayload(BaseModel):
    # IDs of images the user wants to remove from the gallery
    delete_ids: Optional[List[str]] = []