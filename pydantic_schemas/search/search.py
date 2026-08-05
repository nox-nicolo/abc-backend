"""Provides the Search request and response schema module for the backend application."""

from datetime import datetime
from typing import List, Literal, Union
from pydantic import BaseModel

from pydantic import BaseModel
from typing import Literal


class SaveSearchHistoryRequest(BaseModel):
    query: str
    entity: Literal["user", "salon", "service", "hashtag", "post", "query"]
    entity_id: str | None = None


class SearchBase(BaseModel):
    id: str
    entity: str
    score: float | None = None
    
    class Config:
        from_attributes = True  # Pydantic v2 (orm_mode in v1)


class SearchUserResult(SearchBase):
    entity: Literal["user"]
    username: str
    full_name: str | None = None
    avatar_url: str | None = None

class SearchSalonResult(SearchBase):
    entity: Literal["salon"]
    slogan: str
    title: str | None = None
    cover_image: str | None = None
    is_verified: bool
    owner_name: str
    is_saved: bool = False
    

class SearchHashtagResult(SearchBase):
    entity: Literal["hashtag"]
    tag: str
    post_count: int


class SearchServiceResult(SearchBase):
    entity: Literal["service"]
    service_name: str
    category: Literal["major", "minor"]
    parent_service_name: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    currency: str | None = None
    duration_minutes: int | None = None
    image_url: str | None = None
    salon_id: str | None = None
    salon_name: str | None = None
    salon_service_price_id: str | None = None
    is_saved: bool = False


SearchResult = Union[
    SearchUserResult,
    SearchSalonResult,
    SearchHashtagResult,
    SearchServiceResult,
]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    next_cursor: str | None = None



class SaveSearchHistoryResponse(BaseModel):
    success: bool


class SearchHistoryItem(BaseModel):
    id: str
    query: str
    entity: str
    entity_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SearchHistoryResponse(BaseModel):
    items: List[SearchHistoryItem]
