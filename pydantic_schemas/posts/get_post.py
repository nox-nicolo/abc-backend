from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Literal, List


# ───────────────── Location ─────────────────

class LocationSchema(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True


# ───────────────── Media ─────────────────

class MediaSchema(BaseModel):
    url: str
    type: Literal["image", "video", "gif"] = "image"
    aspect_ratio: Optional[float] = None


# ───────────────── Salon (Post Author) ─────────────────

class SalonSchema(BaseModel):
    id: str
    salon_name: str
    username: str
    display_picture: Optional[str] = None
    is_verified: bool = False
    location: Optional[LocationSchema] = None

    class Config:
        from_attributes = True


# ───────────────── Service Meta ─────────────────

class ServiceMetaSchema(BaseModel):
    category: str
    price: float
    duration_minutes: int
    assigned_servicer: Optional[str] = None


# ───────────────── Stats & Viewer State ─────────────────

class PostStatsSchema(BaseModel):
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0


class ViewerStateSchema(BaseModel):
    is_liked: bool = False
    is_saved: bool = False
    is_my_post: bool = False


# ───────────────── Post Response ─────────────────

class PostResponseSchema(BaseModel):
    id: str
    author: SalonSchema

    description: Optional[str] = None
    images: List[MediaSchema]

    service: ServiceMetaSchema

    stats: PostStatsSchema
    viewer_state: ViewerStateSchema

    created_at: datetime

    class Config:
        from_attributes = True


# ───────────────── Likes ─────────────────

class ActorSchema(BaseModel):
    id: str
    username: str
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True


class PostLikeSchema(BaseModel):
    post_id: str
    liked: bool = False
    likes_count: int = Field(default=0, ge=0)
    actor: ActorSchema
