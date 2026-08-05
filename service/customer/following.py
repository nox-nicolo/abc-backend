"""Provides the Following business logic module for customer workflows."""

from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.user import User
from models.profile.salon import Salon
from models.profile.salon import SalonFollower
from pydantic_schemas.pagination import pagination_meta
from pydantic_schemas.customer.following import FollowedSalonItem, MyFollowingResponse

PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"


def get_my_following(
    user_id: str,
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> MyFollowingResponse:
    query = (
        db.query(SalonFollower)
        .options(
            joinedload(SalonFollower.salon)
            .joinedload(Salon.user)
            .joinedload(User.profile_picture)
        )
        .filter(SalonFollower.user_id == user_id)
    )
    total = query.count()
    follows = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for follow in follows:
        salon = follow.salon
        if not salon:
            continue
        user = salon.user
        pic = None
        if user and user.profile_picture and user.profile_picture.file_name:
            pic = f"{PROFILE_IMAGE_BASE}{user.profile_picture.file_name}"
        items.append(
            FollowedSalonItem(
                salon_id=salon.id,
                title=salon.title,
                username=user.username if user else "",
                profile_picture=pic,
            )
        )

    return MyFollowingResponse(
        items=items,
        total=total,
        pagination=pagination_meta(total=total, limit=limit, offset=offset),
    )
