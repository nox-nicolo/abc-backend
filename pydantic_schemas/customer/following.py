from pydantic import BaseModel
from typing import Optional, List


class FollowedSalonItem(BaseModel):
    salon_id: str
    title: str
    username: str
    profile_picture: Optional[str] = None


class MyFollowingResponse(BaseModel):
    items: List[FollowedSalonItem]
    total: int
