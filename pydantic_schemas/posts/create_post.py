# ----------------------------------------------------------------------------------
# Create Post (FINAL CLEAN VERSION)
# ----------------------------------------------------------------------------------

from typing import List, Optional
from pydantic import BaseModel
from core.enumeration import MediaType, MediaState, PostStatus, PostVisibility


# -----------------------
# Media
# -----------------------
class MediaItemSchema(BaseModel):
    media_type: MediaType
    media_state: MediaState
    aspect_ratio: Optional[float] = None
    

# -----------------------
# Post Settings
# -----------------------
class PostSettingsSchema(BaseModel):
    ageRestriction: str
    disableReactions: bool
    enableComments: bool
    allowSharing: bool
    pinned: bool
    showLikes: bool
    showLocation: bool
    visibility: PostVisibility


# -----------------------
# CREATE POST REQUEST BODY
# -----------------------
class CreatePostPayload(BaseModel):
    category: Optional[str]
    caption: Optional[str]
    hashtags: Optional[List[str]]
    tagged: Optional[List[str]]
    media: Optional[List[MediaItemSchema]] 
    settings: PostSettingsSchema
    status: PostStatus 

    # NEW FIELD (from your previous chat – frontend caption font)
    # font: Optional[str] = None
