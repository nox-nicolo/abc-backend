from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CommentAuthor(BaseModel):
    id: str
    username: str
    profile_picture: Optional[str] = None


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_comment_id: Optional[str] = None


class CommentItem(BaseModel):
    id: str
    post_id: str
    content: str
    author: CommentAuthor
    parent_comment_id: Optional[str] = None
    reply_count: int = 0
    created_at: datetime
    is_mine: bool = False


class CommentListResponse(BaseModel):
    items: List[CommentItem]
    next_cursor: Optional[str] = None
