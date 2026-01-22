import json
from typing import Optional
from fastapi import Form
from core.enumeration import PostStatus

class FormPostData:
    """
    Captures all incoming multipart form fields as raw strings.
    JSON-like fields are parsed later.
    """

    def __init__(
        self,
        category: Optional[str] = Form(None),
        caption: Optional[str] = Form(None),
        media_metadata: str = Form("[]"),
        hashtags: str = Form("[]"),
        tagged: str = Form("[]"),
        status: str = Form(...),
        settings: str = Form(...),
    ):
        self.category = category
        self.caption = caption

        # normalize enum (frontend sends lowercase)
        self.status = PostStatus[status.upper()]

        # parse JSON fields
        self.media_metadata = json.loads(media_metadata)
        self.hashtags = json.loads(hashtags)
        self.tagged = json.loads(tagged)
        self.settings = json.loads(settings)
