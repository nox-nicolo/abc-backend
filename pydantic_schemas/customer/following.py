"""Provides the Following request and response schema module for customer workflows."""

from pydantic import BaseModel
from typing import Optional, List

from pydantic_schemas.pagination import PaginationMeta


class FollowedSalonItem(BaseModel):
    salon_id: str
    title: str
    username: str
    profile_picture: Optional[str] = None


class MyFollowingResponse(BaseModel):
    items: List[FollowedSalonItem]
    total: int
    pagination: Optional[PaginationMeta] = None
