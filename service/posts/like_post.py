import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.enumeration import ImageURL
from models.posts.posts import Post, PostLike
from models.auth.user import User
from models.auth.profile_picture import ProfilePicture  # adjust import


PROFILE_PICTURE_BASE_URL = ImageURL.PROFILE_URL.value


async def toggle_like(
    *,
    post_id: str,
    user_id: str,
    db: Session,
):
    # --------------------------------------------------
    # 1. Validate post exists
    # --------------------------------------------------
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # --------------------------------------------------
    # 2. Load actor + profile picture (single query)
    # --------------------------------------------------
    actor = (
        db.query(User)
        .outerjoin(ProfilePicture, ProfilePicture.user_id == User.id)
        .filter(User.id == user_id)
        .first()
    )

    if not actor:
        raise HTTPException(status_code=404, detail="User not found")

    profile_picture_url = None
    if actor.profile_picture:
        profile_picture_url = (
            PROFILE_PICTURE_BASE_URL + actor.profile_picture.file_name
        )

    # --------------------------------------------------
    # 3. Find existing like
    # --------------------------------------------------
    like = (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id,
        )
        .first()
    )

    send_notification = False

    if like:
        like.liked = not like.liked
        if like.liked and post.user_id != user_id:
            send_notification = True
    else:
        like = PostLike(
            id=str(uuid.uuid4()),
            post_id=post_id,
            user_id=user_id,
            liked=True,
        )
        db.add(like)
        if post.user_id != user_id:
            send_notification = True

    db.commit()

    # --------------------------------------------------
    # 4. Count likes
    # --------------------------------------------------
    likes_count = (
        db.query(func.count(PostLike.id))
        .filter(
            PostLike.post_id == post_id,
            PostLike.liked.is_(True),
        )
        .scalar()
    )

    # --------------------------------------------------
    # 5. Notification (LIKE only, not self)
    # --------------------------------------------------
    if send_notification:
        pass
        # await create_notification(...)

    # --------------------------------------------------
    # 6. Response
    # --------------------------------------------------
    return {
        "post_id": post_id,
        "liked": like.liked,
        "likes_count": likes_count,
        "actor": {
            "id": actor.id,
            "username": actor.username,
            "profile_picture": profile_picture_url,
        },
    }
