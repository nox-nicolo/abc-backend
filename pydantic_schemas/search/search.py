from typing import List, Literal, Union
from pydantic import BaseModel

from pydantic import BaseModel
from typing import Literal


class SaveSearchHistoryRequest(BaseModel):
    query: str
    entity: Literal["user", "salon", "service", "hashtag", "post", "query"]
    entity_id: int | None = None


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
    image_url: str | None = None


SearchResult = Union[
    SearchUserResult,
    SearchSalonResult,
    SearchHashtagResult,
    SearchServiceResult,
]

class SearchResponse(BaseModel):
    results: List[SearchResult]



class SaveSearchHistoryResponse(BaseModel):
    success: bool
