from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageURL
from models.auth.user import User
from models.booking.booking import Booking
from models.chat import ChatConversation, ChatMessage
from models.profile.salon import Salon
from pydantic_schemas.chat import ChatSendRequest
from service.notification.notification import create_notification


PROFILE_URL = ImageURL.PROFILE_URL.value


def get_or_create_conversation(
    *,
    db: Session,
    customer_id: str,
    salon_id: str,
    commit: bool = True,
) -> ChatConversation:
    salon = (
        db.query(Salon)
        .options(joinedload(Salon.user).joinedload(User.profile_picture))
        .filter(Salon.id == salon_id)
        .first()
    )
    if not salon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Salon not found")

    if salon.user_id == customer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot chat with your own salon")

    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.customer_id == customer_id,
            ChatConversation.salon_id == salon_id,
        )
        .first()
    )
    if conversation:
        return conversation

    customer = db.query(User).filter(User.id == customer_id).first()
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")

    conversation = ChatConversation(
        customer_id=customer_id,
        salon_id=salon_id,
        salon_user_id=salon.user_id,
    )
    db.add(conversation)
    db.flush()
    if commit:
        db.commit()
        db.refresh(conversation)
    return conversation


def start_conversation(*, db: Session, user_id: str, salon_id: str) -> ChatConversation:
    return get_or_create_conversation(db=db, customer_id=user_id, salon_id=salon_id)


def list_conversations(*, db: Session, user_id: str) -> dict:
    conversations = (
        db.query(ChatConversation)
        .options(
            joinedload(ChatConversation.customer).joinedload(User.profile_picture),
            joinedload(ChatConversation.salon_user).joinedload(User.profile_picture),
            joinedload(ChatConversation.salon),
        )
        .filter(
            or_(
                ChatConversation.customer_id == user_id,
                ChatConversation.salon_user_id == user_id,
            )
        )
        .order_by(ChatConversation.last_message_at.desc().nullslast(), ChatConversation.updated_at.desc())
        .all()
    )
    return {"items": [_conversation_item(c, user_id) for c in conversations]}


def serialize_conversation(*, conversation: ChatConversation, viewer_id: str) -> dict:
    return _conversation_item(conversation, viewer_id)


def get_messages(*, db: Session, user_id: str, conversation_id: str) -> dict:
    conversation = _get_authorized_conversation(db=db, user_id=user_id, conversation_id=conversation_id)
    _mark_read_for_user(conversation, user_id)
    db.commit()

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return {
        "conversation": _conversation_item(conversation, user_id),
        "items": [_message_item(m, user_id) for m in messages],
    }


def send_message(
    *,
    db: Session,
    user_id: str,
    conversation_id: str,
    payload: ChatSendRequest,
) -> ChatMessage:
    conversation = _get_authorized_conversation(db=db, user_id=user_id, conversation_id=conversation_id)
    sender_role = _sender_role(conversation, user_id)
    message = _add_message(
        db=db,
        conversation=conversation,
        sender_user_id=user_id,
        sender_role=sender_role,
        message_type="text",
        body=payload.body.strip(),
        created_by_system=False,
    )
    db.commit()
    db.refresh(message)
    recipient_id = (
        conversation.salon_user_id
        if user_id == conversation.customer_id
        else conversation.customer_id
    )
    create_notification(
        db=db,
        recipient_id=recipient_id,
        actor_id=user_id,
        type="message",
        message=payload.body.strip(),
    )
    return message


def create_booking_chat_event(*, db: Session, booking: Booking, commit: bool = False) -> None:
    conversation = get_or_create_conversation(
        db=db,
        customer_id=booking.customer_id,
        salon_id=booking.salon_id,
        commit=False,
    )
    service = booking.service_name_snapshot or "this service"
    starts = booking.start_at.strftime("%b %d, %H:%M")
    body = f"I booked {service} for {starts}."
    _add_message(
        db=db,
        conversation=conversation,
        sender_user_id=booking.customer_id,
        sender_role="customer",
        message_type="booking_created",
        body=body,
        booking_id=booking.id,
        created_by_system=True,
    )
    if commit:
        db.commit()


def create_booking_confirmed_chat_event(
    *,
    db: Session,
    booking: Booking,
    message: str,
    salon_user_id: str,
    commit: bool = False,
) -> None:
    conversation = get_or_create_conversation(
        db=db,
        customer_id=booking.customer_id,
        salon_id=booking.salon_id,
        commit=False,
    )
    _add_message(
        db=db,
        conversation=conversation,
        sender_user_id=salon_user_id,
        sender_role="salon",
        message_type="booking_confirmed",
        body=message,
        booking_id=booking.id,
        created_by_system=True,
    )
    if commit:
        db.commit()


def create_booking_expired_chat_event(
    *,
    db: Session,
    booking: Booking,
    commit: bool = False,
) -> None:
    conversation = get_or_create_conversation(
        db=db,
        customer_id=booking.customer_id,
        salon_id=booking.salon_id,
        commit=False,
    )
    service = booking.service_name_snapshot or "your service"
    body = (
        f"Your booking request for {service} expired because it was not "
        "confirmed before the appointment time. You can rebook for a new time."
    )
    _add_message(
        db=db,
        conversation=conversation,
        sender_user_id=conversation.salon_user_id,
        sender_role="salon",
        message_type="booking_expired",
        body=body,
        booking_id=booking.id,
        created_by_system=True,
    )
    if commit:
        db.commit()


def _get_authorized_conversation(*, db: Session, user_id: str, conversation_id: str) -> ChatConversation:
    conversation = (
        db.query(ChatConversation)
        .options(
            joinedload(ChatConversation.customer).joinedload(User.profile_picture),
            joinedload(ChatConversation.salon_user).joinedload(User.profile_picture),
            joinedload(ChatConversation.salon),
        )
        .filter(ChatConversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if user_id not in (conversation.customer_id, conversation.salon_user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return conversation


def _add_message(
    *,
    db: Session,
    conversation: ChatConversation,
    sender_user_id: Optional[str],
    sender_role: str,
    message_type: str,
    body: str,
    created_by_system: bool,
    booking_id: Optional[str] = None,
) -> ChatMessage:
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Message cannot be empty")

    now = datetime.now(timezone.utc)
    message = ChatMessage(
        conversation_id=conversation.id,
        sender_user_id=sender_user_id,
        sender_role=sender_role,
        message_type=message_type,
        body=body,
        booking_id=booking_id,
        created_by_system=created_by_system,
        created_at=now,
    )
    db.add(message)

    conversation.last_message_preview = body[:500]
    conversation.last_message_type = message_type
    conversation.last_message_at = now
    conversation.updated_at = now
    if sender_role == "customer":
        conversation.salon_unread_count = (conversation.salon_unread_count or 0) + 1
    elif sender_role == "salon":
        conversation.customer_unread_count = (conversation.customer_unread_count or 0) + 1

    db.flush()
    return message


def _mark_read_for_user(conversation: ChatConversation, user_id: str) -> None:
    if user_id == conversation.customer_id:
        conversation.customer_unread_count = 0
    elif user_id == conversation.salon_user_id:
        conversation.salon_unread_count = 0


def _sender_role(conversation: ChatConversation, user_id: str) -> str:
    if user_id == conversation.customer_id:
        return "customer"
    if user_id == conversation.salon_user_id:
        return "salon"
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")


def _profile_url(user: Optional[User]) -> Optional[str]:
    if not user or not user.profile_picture or not user.profile_picture.file_name:
        return None
    return f"{PROFILE_URL}{user.profile_picture.file_name}"


def _conversation_item(conversation: ChatConversation, viewer_id: str) -> dict:
    return {
        "id": conversation.id,
        "customer_id": conversation.customer_id,
        "customer_name": conversation.customer.name if conversation.customer else "Customer",
        "customer_avatar": _profile_url(conversation.customer),
        "salon_id": conversation.salon_id,
        "salon_name": conversation.salon.title if conversation.salon else "Salon",
        "salon_avatar": _profile_url(conversation.salon_user),
        "last_message_preview": conversation.last_message_preview,
        "last_message_type": conversation.last_message_type,
        "last_message_at": conversation.last_message_at,
        "unread_count": (
            conversation.customer_unread_count
            if viewer_id == conversation.customer_id
            else conversation.salon_unread_count
        ),
    }


def _message_item(message: ChatMessage, viewer_id: str) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_user_id": message.sender_user_id,
        "sender_role": message.sender_role,
        "message_type": message.message_type,
        "body": message.body,
        "booking_id": message.booking_id,
        "created_by_system": message.created_by_system,
        "is_mine": message.sender_user_id == viewer_id,
        "read_at": message.read_at,
        "created_at": message.created_at,
    }
