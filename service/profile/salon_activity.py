"""
Salon activity feed — aggregates recent events from existing tables.

No dedicated activity table; we query bookings, followers, reviews, and
post-likes, merge by timestamp, and return a single chronological list.

Viewer-aware: booking events are owner-only (private). Follower / review /
post-like events are public-safe and returned to everyone.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from core.r2_config import BASE_URL
from core.enumeration import ImageDirectories
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.booking.booking import Booking, ServiceReview
from models.posts.posts import Post, PostLike
from models.profile.salon import Salon, SalonFollower

PROFILE_PIC_DIR = ImageDirectories.PROFILE_DIR.value


def _profile_pic_url(pp: ProfilePicture | None) -> str | None:
    if pp and pp.file_name:
        return f"{BASE_URL}/{PROFILE_PIC_DIR}{pp.file_name}"
    return None


def _actor_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "profile_picture": _profile_pic_url(user.profile_picture),
    }


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _status_value(status) -> str:
    return getattr(status, "value", str(status))


def _stars(value) -> str:
    try:
        rating = int(value or 0)
    except (TypeError, ValueError):
        rating = 0
    rating = max(0, min(5, rating))
    return f"{'★' * rating}{'☆' * (5 - rating)}"


async def get_salon_activity(
    salon_id: str,
    viewer_user_id: str | None,
    db: Session,
    limit: int = 30,
    cursor: str | None = None,
) -> dict:
    """Return recent activity for a salon.

    Owner sees everything (including bookings). Non-owners see only
    public-safe events (followers, reviews, post likes).
    """

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    is_owner = viewer_user_id is not None and salon.user_id == viewer_user_id
    owner_user_id = salon.user_id

    cursor_dt: datetime | None = None
    if cursor:
        try:
            cursor_dt = _as_utc(datetime.fromisoformat(cursor))
        except ValueError:
            cursor_dt = None

    events: List[dict] = []

    # ── 1. Bookings (owner-only) ────────────────────────────────
    if is_owner:
        bq = (
            db.query(Booking)
            .options(joinedload(Booking.customer).joinedload(User.profile_picture))
            .filter(Booking.salon_id == salon_id)
        )
        if cursor_dt:
            bq = bq.filter(Booking.created_at < cursor_dt)
        bookings = bq.order_by(desc(Booking.created_at)).limit(limit).all()

        for b in bookings:
            actor = _actor_dict(b.customer) if b.customer else None
            name = actor["name"] if actor else "Someone"
            svc = b.service_name_snapshot or "a service"
            booking_status = _status_value(b.status)

            if booking_status == "completed":
                evt_type = "booking_completed"
                msg = f"{name} completed their booking for {svc}"
            elif booking_status == "cancelled":
                evt_type = "booking_cancelled"
                msg = f"Booking for {svc} by {name} was cancelled"
            else:
                evt_type = "booking_new"
                msg = f"{name} booked {svc}"

            events.append({
                "id": f"bk_{b.id}",
                "type": evt_type,
                "message": msg,
                "actor": actor,
                "created_at": _as_utc(b.created_at),
                "ref_id": b.id,
            })

    # ── 2. New followers (public) ───────────────────────────────
    fq = (
        db.query(SalonFollower)
        .options(joinedload(SalonFollower.user).joinedload(User.profile_picture))
        .filter(SalonFollower.salon_id == salon_id)
    )
    if cursor_dt:
        fq = fq.filter(SalonFollower.created_at < cursor_dt)
    followers = fq.order_by(desc(SalonFollower.created_at)).limit(limit).all()

    for f in followers:
        actor = _actor_dict(f.user) if f.user else None
        name = actor["name"] if actor else "Someone"
        events.append({
            "id": f"fl_{f.id}",
            "type": "follower_new",
            "message": f"{name} started following",
            "actor": actor,
            "created_at": _as_utc(f.created_at),
            "ref_id": f.user_id if f.user else None,
        })

    # ── 3. New reviews (public) ─────────────────────────────────
    rq = (
        db.query(ServiceReview)
        .options(joinedload(ServiceReview.user).joinedload(User.profile_picture))
        .filter(ServiceReview.salon_id == salon_id)
    )
    if cursor_dt:
        rq = rq.filter(ServiceReview.created_at < cursor_dt)
    reviews = rq.order_by(desc(ServiceReview.created_at)).limit(limit).all()

    for r in reviews:
        actor = _actor_dict(r.user) if r.user else None
        name = actor["name"] if actor else "Someone"
        stars = _stars(r.rating)
        events.append({
            "id": f"rv_{r.id}",
            "type": "review_new",
            "message": f"{name} left a {stars} review",
            "actor": actor,
            "created_at": _as_utc(r.created_at),
            "ref_id": r.booking_id,
        })

    # ── 4. Post likes (public) ──────────────────────────────────
    lq = (
        db.query(PostLike)
        .options(joinedload(PostLike.user).joinedload(User.profile_picture))
        .join(Post, Post.id == PostLike.post_id)
        .filter(
            Post.user_id == owner_user_id,
            PostLike.liked.is_(True),
            PostLike.user_id != owner_user_id,  # exclude self-likes
        )
    )
    if cursor_dt:
        lq = lq.filter(PostLike.created_at < cursor_dt)
    likes = lq.order_by(desc(PostLike.created_at)).limit(limit).all()

    for lk in likes:
        actor = _actor_dict(lk.user) if lk.user else None
        name = actor["name"] if actor else "Someone"
        events.append({
            "id": f"lk_{lk.id}",
            "type": "post_like",
            "message": f"{name} liked a post",
            "actor": actor,
            "created_at": _as_utc(lk.created_at),
            "ref_id": lk.post_id,
        })

    # ── Merge and paginate ──────────────────────────────────────
    events.sort(key=lambda e: e["created_at"], reverse=True)
    events = events[:limit]

    next_cursor = None
    if len(events) == limit:
        last_dt = events[-1]["created_at"]
        if isinstance(last_dt, datetime):
            next_cursor = _as_utc(last_dt).isoformat()

    return {
        "items": events,
        "next_cursor": next_cursor,
    }
