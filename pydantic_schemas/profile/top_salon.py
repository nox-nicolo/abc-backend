"""Provides the Top Salon request and response schema module for profile workflows."""

from pydantic import BaseModel
from typing import Optional, List
from pydantic_schemas.pagination import PaginationMeta

class TopSalonCard(BaseModel):
    salon_id: str
    name: str
    logo_url: Optional[str]
    cover_url: Optional[str]
    city: Optional[str]
    tagline: Optional[str]


class TopSalonResponse(BaseModel):
    results: List[TopSalonCard]
    pagination: Optional[PaginationMeta] = None
