"""Provides the Chat request and response schema module for the backend application."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatStartRequest(BaseModel):
    salon_id: str


class ChatSendRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class ChatConversationItem(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    customer_avatar: Optional[str] = None
    salon_id: str
    salon_name: str
    salon_avatar: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_type: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


class ChatConversationListResponse(BaseModel):
    items: List[ChatConversationItem]


class ChatMessageItem(BaseModel):
    id: str
    conversation_id: str
    sender_user_id: Optional[str] = None
    sender_role: str
    message_type: str
    body: str
    booking_id: Optional[str] = None
    created_by_system: bool
    is_mine: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    conversation: ChatConversationItem
    items: List[ChatMessageItem]
