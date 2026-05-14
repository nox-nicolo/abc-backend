from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import distinct, func

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.user import User
from models.booking.booking import Booking
from models.notifications.notification import Notification, NotificationSendLog
from models.posts.posts import PostComment
from models.profile.salon import Salon, SalonFollower
from models.profile.notification_preferences import UserNotificationPreference
from pydantic_schemas.notifications.notification import (
    NotificationActor,
    NotificationItem,
    NotificationListResponse,
    SalonEventCampaignRequest,
    SalonEventCampaignResponse,
    SalonPromotionCampaignRequest,
    SalonPromotionCampaignResponse,
    UnreadCountResponse,
)
from service.users.mutes import muted_target_ids
from service.notification.push import send_push_to_user
from service.notification.booking_ai import (
    EventBookingNotificationContext,
    PromotionNotificationContext,
    generate_event_based_booking_message,
    generate_promotion_message,
)


PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"

PREVIEW_MAX_LEN = 140
SALON_BOOKING_LINK_BASE = "africanbeauty://salon"


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


def _actor_schema(user: User) -> NotificationActor:
    return NotificationActor(
        id=user.id,
        username=user.username,
        profile_picture=_avatar_url(user),
        role=user.role,
        salon_id=user.salon.id if user.salon else None,
    )


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
    message: Optional[str] = None,
    commit: bool = True,
) -> Notification:
    """
    Insert an in-app notification. Safe to call within an existing
    transaction — pass commit=False to let the caller flush.
    Skips self-actions silently (recipient == actor).
    """
    if recipient_id == actor_id:
        return None  # type: ignore[return-value]
    if not _notification_allowed(db=db, recipient_id=recipient_id, type=type):
        return None  # type: ignore[return-value]

    notif = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=type,
        post_id=post_id,
        comment_id=comment_id,
        booking_id=booking_id,
        message=message,
        delivery_status="created",
    )
    db.add(notif)
    if commit:
        db.flush()
        notif.delivery_status = "sent"
        db.commit()
        db.refresh(notif)
        _send_notification_push(
            db=db,
            notification=notif,
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=type,
            post_id=post_id,
            comment_id=comment_id,
            booking_id=booking_id,
            message=message,
            commit_changes=True,
        )
    else:
        db.flush()
        notif.delivery_status = "sent"
        db.flush()
        _send_notification_push(
            db=db,
            notification=notif,
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=type,
            post_id=post_id,
            comment_id=comment_id,
            booking_id=booking_id,
            message=message,
            commit_changes=False,
        )
    return notif


def create_welcome_notification(
    *,
    db: Session,
    user_id: str,
    commit: bool = True,
) -> Optional[Notification]:
    existing = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.actor_id == user_id,
            Notification.type == "welcome",
        )
        .first()
    )
    if existing:
        return existing

    message = (
        "Welcome to African Beauty. Your beauty community is ready: discover "
        "salons, save favorites, book with confidence, and grow with the family."
    )
    notif = Notification(
        recipient_id=user_id,
        actor_id=user_id,
        type="welcome",
        message=message,
        delivery_status="created",
    )
    db.add(notif)
    db.flush()
    notif.delivery_status = "sent"

    if commit:
        db.commit()
        db.refresh(notif)
    else:
        db.flush()

    send_push_to_user(
        db=db,
        user_id=user_id,
        title="Welcome to African Beauty",
        body=message,
        data={
            "notification_id": notif.id,
            "type": "welcome",
            "post_id": "",
            "comment_id": "",
            "booking_id": "",
        },
        commit_changes=commit,
    )
    return notif


def _send_notification_push(
    *,
    db: Session,
    notification: Notification,
    recipient_id: str,
    actor_id: str,
    type: str,
    post_id: Optional[str],
    comment_id: Optional[str],
    booking_id: Optional[str],
    message: Optional[str],
    commit_changes: bool,
) -> None:
    title, body = _push_copy(
        db=db,
        actor_id=actor_id,
        type=type,
        message=message,
    )
    send_push_to_user(
        db=db,
        user_id=recipient_id,
        title=title,
        body=body,
        data={
            "notification_id": notification.id,
            "type": type,
            "post_id": post_id or "",
            "comment_id": comment_id or "",
            "booking_id": booking_id or "",
        },
        commit_changes=commit_changes,
    )


def _push_copy(
    *,
    db: Session,
    actor_id: str,
    type: str,
    message: Optional[str],
) -> tuple[str, str]:
    actor = db.query(User).filter(User.id == actor_id).first()
    actor_name = actor.username if actor and actor.username else "Someone"

    if message:
        if type == "welcome":
            return "Welcome to African Beauty", _truncate(message) or "Welcome to the family"
        if type.startswith("booking_"):
            return "Booking update", _truncate(message) or "You have a booking update"
        return "African Beauty", _truncate(message) or "You have a new notification"

    copy = {
        "welcome": ("Welcome to African Beauty", "Welcome to the family"),
        "like": ("New like", f"{actor_name} liked your post"),
        "comment": ("New comment", f"{actor_name} commented on your post"),
        "reply": ("New reply", f"{actor_name} replied to your comment"),
        "message": ("New message", f"{actor_name} sent you a message"),
        "booking_new": ("New booking", f"{actor_name} requested a booking"),
        "booking_confirmed": ("Booking confirmed", "Your booking was confirmed"),
        "booking_rejected": ("Booking declined", "Your booking was declined"),
        "booking_cancelled": ("Booking cancelled", f"{actor_name} cancelled a booking"),
        "booking_completed": ("Booking completed", "Your booking was completed"),
        "booking_no_show": ("Booking no-show", "A booking was marked as no-show"),
        "booking_rescheduled": ("Booking rescheduled", f"{actor_name} rescheduled a booking"),
        "booking_reminder_ai": ("Booking reminder", "You have an upcoming booking"),
        "rebooking_reminder_ai": ("Time to book again", "A salon you visited is ready for you"),
        "salon_event_marketing": ("Salon event", "A salon shared a new event"),
        "event_based_booking": ("Booking idea", "A salon has a suggestion for your next visit"),
        "salon_promotion_campaign": ("Salon offer", "A salon shared a new offer"),
    }
    return copy.get(type, ("African Beauty", "You have a new notification"))


def _notification_allowed(*, db: Session, recipient_id: str, type: str) -> bool:
    pref = (
        db.query(UserNotificationPreference)
        .filter(UserNotificationPreference.user_id == recipient_id)
        .first()
    )
    if pref is None:
        return True

    if type in ("like", "like_grouped"):
        return pref.allow_likes
    if type in ("comment", "reply"):
        return pref.allow_comments
    if type in ("booking_reminder_ai", "rebooking_reminder_ai"):
        return pref.allow_reminders
    if type.startswith("booking_"):
        return pref.allow_bookings
    if type in ("salon_event_marketing", "event_based_booking", "salon_promotion_campaign"):
        return pref.allow_promotions
    return True


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

    muted_users = muted_target_ids(db=db, user_id=user_id, target_type="user")
    muted_posts = muted_target_ids(db=db, user_id=user_id, target_type="post")
    muted_salons = muted_target_ids(db=db, user_id=user_id, target_type="salon")

    query = (
        db.query(Notification)
        .options(
            joinedload(Notification.actor).joinedload(User.profile_picture),
            joinedload(Notification.actor).joinedload(User.salon),
        )
        .filter(Notification.recipient_id == user_id)
    )
    if muted_users:
        query = query.filter(~Notification.actor_id.in_(muted_users))
    if muted_posts:
        query = query.filter(~Notification.post_id.in_(muted_posts))
    if cursor_dt:
        query = query.filter(Notification.created_at < cursor_dt)

    # Fetch extra rows because several likes can collapse into one grouped row.
    rows = (
        query.order_by(Notification.created_at.desc())
        .limit(limit * 4)
        .all()
    )

    comment_ids = [n.comment_id for n in rows if n.comment_id]
    preview_map: dict[str, str] = {}
    if comment_ids:
        comments = (
            db.query(PostComment)
            .filter(PostComment.id.in_(comment_ids))
            .all()
        )
        preview_map = {c.id: c.content for c in comments}

    items: list[NotificationItem] = []
    grouped_like_posts: set[str] = set()

    for n in rows:
        if n.actor and n.actor.salon and n.actor.salon.id in muted_salons:
            continue
        if len(items) >= limit:
            break

        if n.type == "like" and n.post_id:
            if n.post_id in grouped_like_posts:
                continue
            grouped_like_posts.add(n.post_id)
            items.append(_grouped_like_item(db=db, notification=n, user_id=user_id))
            continue

        items.append(
            NotificationItem(
                id=n.id,
                type=n.type,
                actor=_actor_schema(n.actor),
                post_id=n.post_id,
                comment_id=n.comment_id,
                booking_id=n.booking_id,
                preview=_truncate(n.message or preview_map.get(n.comment_id)),
                is_grouped=False,
                group_count=1,
                is_read=n.is_read,
                delivery_status=n.delivery_status or ("read" if n.is_read else "sent"),
                created_at=n.created_at,
            )
        )

    next_cursor = rows[-1].created_at.isoformat() if len(rows) == limit * 4 else None
    return NotificationListResponse(items=items, next_cursor=next_cursor)


def _grouped_like_item(*, db: Session, notification: Notification, user_id: str) -> NotificationItem:
    actor_rows = (
        db.query(Notification.actor_id)
        .filter(
            Notification.recipient_id == user_id,
            Notification.type == "like",
            Notification.post_id == notification.post_id,
        )
        .distinct()
        .all()
    )
    group_count = len(actor_rows)
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.recipient_id == user_id,
            Notification.type == "like",
            Notification.post_id == notification.post_id,
            Notification.is_read.is_(False),
        )
        .scalar()
        or 0
    )
    actor_name = notification.actor.username
    if group_count <= 1:
        preview = f"{actor_name} liked your post"
    else:
        preview = f"{actor_name} and {group_count - 1} others liked your post"

    return NotificationItem(
        id=notification.id,
        type="like_grouped" if group_count > 1 else "like",
        actor=_actor_schema(notification.actor),
        post_id=notification.post_id,
        comment_id=None,
        booking_id=None,
        preview=_truncate(preview),
        is_grouped=group_count > 1,
        group_count=group_count,
        is_read=unread_count == 0,
        delivery_status="read" if unread_count == 0 else "sent",
        created_at=notification.created_at,
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
        .update(
            {Notification.is_read: True, Notification.delivery_status: "read"},
            synchronize_session=False,
        )
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
    if notif.type == "like" and notif.post_id:
        db.query(Notification).filter(
            Notification.recipient_id == user_id,
            Notification.type == "like",
            Notification.post_id == notif.post_id,
            Notification.is_read.is_(False),
        ).update(
            {Notification.is_read: True, Notification.delivery_status: "read"},
            synchronize_session=False,
        )
        db.commit()
        return {"id": notification_id, "is_read": True}
    if not notif.is_read:
        notif.is_read = True
        notif.delivery_status = "read"
        db.commit()
    return {"id": notification_id, "is_read": True}


def create_salon_event_campaign(
    *,
    db: Session,
    owner_user_id: str,
    payload: SalonEventCampaignRequest,
) -> SalonEventCampaignResponse:
    salon = db.query(Salon).filter(Salon.user_id == owner_user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    recipients = _event_campaign_recipients(
        db=db,
        salon_id=salon.id,
        target_group=payload.target_group,
        limit=payload.max_recipients,
    )
    booking_link = payload.booking_link or f"{SALON_BOOKING_LINK_BASE}/{salon.id}/booking"
    cycle_key = _event_campaign_cycle_key(
        salon_id=salon.id,
        event=payload.upcoming_event,
        service=payload.service_type,
        days_until_event=payload.days_until_event,
        target_group=payload.target_group,
    )

    sent = 0
    skipped_duplicates = 0
    sample_message = None

    for customer in recipients:
        if customer.id == owner_user_id:
            continue
        if count_sends_for_cycle(
            db=db,
            recipient_id=customer.id,
            cycle_key=cycle_key,
            type="salon_event_marketing",
        ):
            skipped_duplicates += 1
            continue

        generated = generate_event_based_booking_message(
            EventBookingNotificationContext(
                customer_name=customer.name or customer.username or "there",
                upcoming_event=payload.upcoming_event,
                days_until_event=payload.days_until_event,
                salon_name=salon.title,
                stylist_name=payload.stylist_name,
                service_type=payload.service_type,
                booking_link=booking_link,
            )
        )
        message = generated["message"]
        sample_message = sample_message or message
        notification = create_notification(
            db=db,
            recipient_id=customer.id,
            actor_id=owner_user_id,
            type="salon_event_marketing",
            message=message,
            commit=False,
        )
        if notification is None:
            continue
        log_notification_send(
            db=db,
            recipient_id=customer.id,
            actor_id=owner_user_id,
            notification_id=notification.id,
            type="salon_event_marketing",
            cycle_key=cycle_key,
            message=message,
        )
        sent += 1

    db.commit()
    return SalonEventCampaignResponse(
        channel="in app notification",
        trigger="event_based",
        target_group=payload.target_group,
        recipients_found=len(recipients),
        sent=sent,
        skipped_duplicates=skipped_duplicates,
        sample_message=sample_message,
    )


def create_salon_promotion_campaign(
    *,
    db: Session,
    owner_user_id: str,
    payload: SalonPromotionCampaignRequest,
) -> SalonPromotionCampaignResponse:
    salon = db.query(Salon).filter(Salon.user_id == owner_user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    recipients = _event_campaign_recipients(
        db=db,
        salon_id=salon.id,
        target_group=payload.target_group,
        limit=payload.max_recipients,
    )
    booking_link = payload.booking_link or f"{SALON_BOOKING_LINK_BASE}/{salon.id}/booking"
    cycle_key = _promotion_campaign_cycle_key(
        salon_id=salon.id,
        offer=payload.offer_title,
        service=payload.service_type,
        target_group=payload.target_group,
        discount_code=payload.discount_code,
    )

    sent = 0
    skipped_duplicates = 0
    sample_message = None

    for customer in recipients:
        if customer.id == owner_user_id:
            continue
        if count_sends_for_cycle(
            db=db,
            recipient_id=customer.id,
            cycle_key=cycle_key,
            type="salon_promotion_campaign",
        ):
            skipped_duplicates += 1
            continue

        generated = generate_promotion_message(
            PromotionNotificationContext(
                customer_name=customer.name or customer.username or "there",
                salon_name=salon.title,
                offer_title=payload.offer_title,
                service_type=payload.service_type,
                discount_code=payload.discount_code,
                expires_at=payload.expires_at,
                stylist_name=payload.stylist_name,
                booking_link=booking_link,
            )
        )
        message = generated["message"]
        sample_message = sample_message or message
        notification = create_notification(
            db=db,
            recipient_id=customer.id,
            actor_id=owner_user_id,
            type="salon_promotion_campaign",
            message=message,
            commit=False,
        )
        if notification is None:
            continue
        log_notification_send(
            db=db,
            recipient_id=customer.id,
            actor_id=owner_user_id,
            notification_id=notification.id,
            type="salon_promotion_campaign",
            cycle_key=cycle_key,
            message=message,
        )
        sent += 1

    db.commit()
    return SalonPromotionCampaignResponse(
        channel="in app notification",
        trigger="promotion_campaign",
        target_group=payload.target_group,
        recipients_found=len(recipients),
        sent=sent,
        skipped_duplicates=skipped_duplicates,
        sample_message=sample_message,
    )


def count_sends_for_cycle(
    *,
    db: Session,
    recipient_id: str,
    cycle_key: str,
    type: str,
) -> int:
    return (
        db.query(NotificationSendLog)
        .filter(
            NotificationSendLog.recipient_id == recipient_id,
            NotificationSendLog.cycle_key == cycle_key,
            NotificationSendLog.type == type,
        )
        .count()
    )


def _event_campaign_recipients(
    *,
    db: Session,
    salon_id: str,
    target_group: str,
    limit: int,
) -> list[User]:
    user_ids: set[str] = set()

    if target_group in ("followers", "all_engaged"):
        follower_rows = (
            db.query(SalonFollower.user_id)
            .filter(
                SalonFollower.salon_id == salon_id,
                SalonFollower.notifications_enabled.is_(True),
            )
            .limit(limit)
            .all()
        )
        user_ids.update(row.user_id for row in follower_rows)

    if target_group in ("past_customers", "all_engaged"):
        booking_rows = (
            db.query(distinct(Booking.customer_id).label("customer_id"))
            .filter(Booking.salon_id == salon_id)
            .limit(limit)
            .all()
        )
        user_ids.update(row.customer_id for row in booking_rows)

    if not user_ids:
        return []

    return (
        db.query(User)
        .filter(User.id.in_(list(user_ids)))
        .limit(limit)
        .all()
    )


def _event_campaign_cycle_key(
    *,
    salon_id: str,
    event: str,
    service: str,
    days_until_event: int,
    target_group: str,
) -> str:
    event_key = "_".join(event.lower().split())[:40]
    service_key = "_".join(service.lower().split())[:40]
    return f"salon_event:{salon_id}:{target_group}:{event_key}:{service_key}:{days_until_event}"


def _promotion_campaign_cycle_key(
    *,
    salon_id: str,
    offer: str,
    service: str,
    target_group: str,
    discount_code: Optional[str],
) -> str:
    offer_key = "_".join(offer.lower().split())[:40]
    service_key = "_".join(service.lower().split())[:40]
    code_key = "_".join((discount_code or "no_code").lower().split())[:30]
    return f"salon_promo:{salon_id}:{target_group}:{offer_key}:{service_key}:{code_key}"


def log_notification_send(
    *,
    db: Session,
    recipient_id: str,
    actor_id: str,
    type: str,
    cycle_key: str,
    message: str,
    notification_id: Optional[str] = None,
    booking_id: Optional[str] = None,
) -> NotificationSendLog:
    current_count = count_sends_for_cycle(
        db=db,
        recipient_id=recipient_id,
        cycle_key=cycle_key,
        type=type,
    )
    row = NotificationSendLog(
        recipient_id=recipient_id,
        actor_id=actor_id,
        notification_id=notification_id,
        booking_id=booking_id,
        cycle_key=cycle_key,
        type=type,
        message=message,
        send_count=current_count + 1,
    )
    db.add(row)
    db.flush()
    return row
