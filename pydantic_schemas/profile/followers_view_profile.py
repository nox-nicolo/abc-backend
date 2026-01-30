from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from core.enumeration import ImageURL
from models.profile.salon import SalonFollower
from models.auth.user import User
from models.auth.profile_picture import ProfilePicture

PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value


def get_salon_followers(
    *,
    db: Session,
    salon_id: str,
    viewer_id: Optional[str],
    limit: int = 20,
    cursor: Optional[str] = None,
):
    query = (
        db.query(SalonFollower, User)
        .join(User, User.id == SalonFollower.user_id)
        .filter(SalonFollower.salon_id == salon_id)
        .order_by(SalonFollower.created_at.desc())
    )

    # ───── Cursor pagination ─────
    if cursor:
        query = query.filter(SalonFollower.created_at < cursor)

    rows = query.limit(limit + 1).all()

    # ───── Total count ─────
    total_count = (
        db.query(func.count(SalonFollower.id))
        .filter(SalonFollower.salon_id == salon_id)
        .scalar()
        or 0
    )

    items = []
    next_cursor = None

    for follower, user in rows[:limit]:
        profile_picture = (
            db.query(ProfilePicture)
            .filter(ProfilePicture.user_id == user.id)
            .first()
        )

        avatar_url = (
            f"{PROFILE_IMAGE_BASE}{profile_picture.file_name}"
            if profile_picture
            else None
        )

        # viewer follows THIS user?
        is_following = False
        if viewer_id:
            is_following = (
                db.query(SalonFollower)
                .filter(
                    SalonFollower.user_id == viewer_id,
                    SalonFollower.salon_id == salon_id,
                )
                .first()
                is not None
            )

        items.append(
            {
                "user_id": user.id,
                "username": user.username,
                "name": user.name,
                "avatar": avatar_url,
                "is_following": is_following,
            }
        )

    # ───── next cursor ─────
    if len(rows) > limit:
        next_cursor = rows[limit][0].created_at.isoformat()

    return {
        "count": total_count,
        "items": items,
        "next_cursor": next_cursor,
    }
