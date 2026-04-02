from pydantic import BaseModel
from typing import Optional, List


class CustomerStatsSchema(BaseModel):
    following_count: int = 0
    bookings_count: int = 0
    reviews_count: int = 0


class CustomerProfileResponse(BaseModel):
    id: str
    username: str
    name: str
    profile_picture: Optional[str] = None

    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None

    preferred_services: List[str] = []
    stats: CustomerStatsSchema

    is_salon_owner: bool = False


class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
