# hashtag results
from typing import List, Optional
from pydantic import BaseModel


class PostImagePreviewOut(BaseModel):
    url: str

    class Config:
        from_attributes = True
        

class HashtagPostTileOut(BaseModel):
    post_id: str
    image: PostImagePreviewOut

    class Config:
        from_attributes = True
        

class HashtagHeaderOut(BaseModel):
    name: str
    post_count: int
    is_trending: bool

    class Config:
        from_attributes = True


class HashtagGridOut(BaseModel):
    hashtag: HashtagHeaderOut
    posts: List[HashtagPostTileOut]
    cursor: Optional[str] = None
