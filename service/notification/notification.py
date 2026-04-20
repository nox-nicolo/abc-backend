from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.user import User
from models.notifications.notification import Notification
from models.posts.posts import PostComment
from pydantic_schemas.notifications.notification import (
    NotificationActor,
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
)


PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"

PREVIEW_MAX_LEN = 140


def _avatar_url(user: Optional[User]) -> Optional[str]:
    if not user or not user.profile_picture or not user.profile_picture.file_name:
        return None
    return f"{PROFILE_IMAGE_BASE}{user.profile_picture.file_name}"


def _truncate(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    if len(text) <= PREVIEW_MAX_LEN:
        return text
    return text[: PREVIEW_MAX_LEN - 1].rstrip() + "…"


# ------------------------------------------------------------------
# CREATE — called from event hooks (like, comment, reply)
# ------------------------------------------------------------------
def create_notification(
    *,
    db: Session,
    recipient_id: str,
    actor_id: str,
    type: str,
    post_id: Optional[str] = None,
    comment_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    commit: bool = True,
) -> Notification:
    """
    Insert an in-app notification. Safe to call within an existing
    transaction — pass commit=False to let the caller flush.
    Skips self-actions silently (recipient == actor).
    """
    if recipient_id == actor_id:
        return None  # type: ignore[return-value]

    notif = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=type,
        post_id=post_id,
        comment_id=comment_id,
        booking_id=booking_id,
    )
    db.add(notif)
    if commit:
        db.commit()
        db.refresh(notif)
    else:
        db.flush()
    return notif


# ------------------------------------------------------------------
# LIST — cursor-paginated, eager-loads actor + comment preview
# ------------------------------------------------------------------
def list_notifications(
    *,
    db: Session,
    user_id: str,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> NotificationListResponse:
    cursor_dt: Optional[datetime] = None
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    query = (
        db.query(Notification)
        .options(
            joinedload(Notification.actor).joinedload(User.profile_picture),
        )
        .filter(Notification.recipient_id == user_id)
    )
    if cursor_dt:
        query = query.filter(Notification.created_at < cursor_dt)

    rows = (
        query.order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )

    # fetch comment previews in one shot for comment/reply types
    comment_ids = [n.comment_id for n in rows if n.comment_id]
    preview_map: dict[str, str] = {}
    if comment_ids:
        comments = (
            db.query(PostComment)
            .filter(PostComment.id.in_(comment_ids))
            .all()
        )
        preview_map = {c.id: c.content for c in comments}

    items = [
        NotificationItem(
            id=n.id,
            type=n.type,
            actor=NotificationActor(
                id=n.actor.id,
                username=n.actor.username,
                profile_picture=_avatar_url(n.actor),
            ),
            post_id=n.post_id,
            comment_id=n.comment_id,
            booking_id=n.booking_id,
            preview=_truncate(preview_map.get(n.comment_id)) if n.comment_id else None,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in rows
    ]

    return NotificationListResponse(
        items=items,
        next_cursor=rows[-1].created_at.isoformat() if rows else None,
    )


# ------------------------------------------------------------------
# UNREAD COUNT
# ------------------------------------------------------------------
def get_unread_count(*, db: Session, user_id: str) -> UnreadCountResponse:
    count = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.is_read.is_(False),
        )
        .count()
    )
    return UnreadCountResponse(unread=count)


# ------------------------------------------------------------------
# MARK AS READ
# ------------------------------------------------------------------
def mark_all_read(*, db: Session, user_id: str) -> dict:
    updated = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.is_read.is_(False),
        )
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


def mark_read(*, db: Session, user_id: str, notification_id: str) -> dict:
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not notif.is_read:
        notif.is_read = True
        db.commit()
    return {"id": notification_id, "is_read": True}
