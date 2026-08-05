"""Provides the Chat API route module for the backend application."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.rate_limit import enforce_rate_limit
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.chat import (
    ChatConversationItem,
    ChatConversationListResponse,
    ChatMessageItem,
    ChatMessageListResponse,
    ChatSendRequest,
    ChatStartRequest,
)
from service.auth.JWT.oauth2 import get_current_user
from service.chat import (
    get_messages,
    list_conversations,
    send_message,
    serialize_conversation,
    start_conversation,
)


chat = APIRouter(prefix="/chat", tags=["Chat"])


@chat.get("/conversations", response_model=ChatConversationListResponse)
def conversations(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_conversations(db=db, user_id=current_user.user_id)


@chat.post("/conversations", response_model=ChatConversationItem)
def open_conversation(
    payload: ChatStartRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = start_conversation(
        db=db,
        user_id=current_user.user_id,
        salon_id=payload.salon_id,
    )
    return serialize_conversation(conversation=conversation, viewer_id=current_user.user_id)


@chat.get("/conversations/{conversation_id}/messages", response_model=ChatMessageListResponse)
def conversation_messages(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_messages(
        db=db,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )


@chat.post("/conversations/{conversation_id}/messages", response_model=ChatMessageItem)
def create_message(
    conversation_id: str,
    payload: ChatSendRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        bucket="chat:send",
        limit=60,
        window_seconds=60,
        user_id=current_user.user_id,
    )
    message = send_message(
        db=db,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
        payload=payload,
    )
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_user_id": message.sender_user_id,
        "sender_role": message.sender_role,
        "message_type": message.message_type,
        "body": message.body,
        "booking_id": message.booking_id,
        "created_by_system": message.created_by_system,
        "is_mine": True,
        "read_at": message.read_at,
        "created_at": message.created_at,
    }
