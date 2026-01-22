from pydantic import BaseModel
from typing import List, Optional

class PostSettings(BaseModel):
    visibility: str
    showLikes: bool
    enableComments: bool
    allowSharing: bool
    showLocation: bool
    pinned: bool
    ageRestriction: bool
    disableReactions: bool

class CreatePostModel(BaseModel):
    author: str
    category: str
    caption: Optional[str] = None
    hashtags: List[str] = []
    tagged: List[str] = []
    settings: PostSettings
