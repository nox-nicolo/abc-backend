"""Provides the Reaction request and response schema module for posts workflows."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class PostReactionRequest(BaseModel):
    reaction: str = Field(..., min_length=1, max_length=24)


class PostReactionResponse(BaseModel):
    post_id: str
    my_reaction: Optional[str] = None
    reactions: Dict[str, int]
    disabled: bool = False


class PostShareRequest(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=20)
    message: Optional[str] = Field(None, max_length=500)


class PostShareResponse(BaseModel):
    post_id: str
    shared_count: int
    message: str
