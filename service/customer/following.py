from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.profile.salon import SalonFollower
from pydantic_schemas.customer.following import FollowedSalonItem, MyFollowingResponse

PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"


def get_my_following(user_id: str, db: Session) -> MyFollowingResponse:
    follows = (
        db.query(SalonFollower)
        .options(
            joinedload(SalonFollower.salon)
            .joinedload("user")
            .joinedload("profile_picture")
        )
        .filter(SalonFollower.user_id == user_id)
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

    return MyFollowingResponse(items=items, total=len(items))
