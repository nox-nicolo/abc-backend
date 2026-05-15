import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.enumeration import PostVisibility
from models.auth.user import User
from models.posts.posts import Post, PostShare
from models.profile.salon import Salon, SalonFollower
from pydantic_schemas.posts.reaction import PostShareRequest
from service.notification.notification import create_notification


def _viewer_follows_post_salon(*, post: Post, user_id: str, db: Session) -> bool:
    salon = db.query(Salon).filter(Salon.user_id == post.user_id).first()
    if not salon:
        return False
    return (
        db.query(SalonFollower.id)
        .filter(
            SalonFollower.salon_id == salon.id,
            SalonFollower.user_id == user_id,
        )
        .first()
        is not None
    )


def can_view_post_for_share(*, post: Post, user_id: str, db: Session) -> bool:
    if post.user_id == user_id:
        return True

    settings = post.settings
    if not settings:
        return True
    if settings.visibility == PostVisibility.PRIVATE:
        return False
    if settings.visibility == PostVisibility.FRIENDS:
        return _viewer_follows_post_salon(post=post, user_id=user_id, db=db)
    return True


def can_share_post(*, post: Post, user_id: str, db: Session) -> bool:
    if not can_view_post_for_share(post=post, user_id=user_id, db=db):
        return False

    settings = post.settings
    if post.user_id != user_id and settings and settings.allow_share is False:
        return False

    return True


def repost_(*, post_id: str, user_id: str, db: Session):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if not can_view_post_for_share(post=post, user_id=user_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot share this post",
        )

    if not can_share_post(post=post, user_id=user_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sharing is disabled for this post",
        )

    # Check if already reposted by this user
    existing = (
        db.query(PostShare)
        .filter(PostShare.post_id == post_id, PostShare.share_user_id == user_id)
        .first()
    )
    if existing:
        # Undo repost
        db.delete(existing)
        db.commit()
        return {"reposted": False}

    share = PostShare(
        id=str(uuid.uuid4()),
        post_id=post_id,
        share_user_id=user_id,
        user_id=None,  # public repost, not directed at a specific user
    )
    db.add(share)
    db.commit()
    return {"reposted": True}


def share_post_to_users(
    *,
    post_id: str,
    user_id: str,
    payload: PostShareRequest,
    db: Session,
) -> dict:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if not can_share_post(post=post, user_id=user_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sharing is disabled for this post",
        )

    recipients = list(dict.fromkeys(uid for uid in payload.user_ids if uid != user_id))
    if not recipients:
        raise HTTPException(status_code=400, detail="Select at least one recipient")

    existing_users = {
        row[0]
        for row in db.query(User.id).filter(User.id.in_(recipients)).all()
    }
    if not existing_users:
        raise HTTPException(status_code=404, detail="No recipients found")

    shared_count = 0
    for recipient_id in existing_users:
        exists = (
            db.query(PostShare)
            .filter(
                PostShare.post_id == post_id,
                PostShare.share_user_id == user_id,
                PostShare.user_id == recipient_id,
            )
            .first()
        )
        if exists:
            continue

        db.add(
            PostShare(
                id=str(uuid.uuid4()),
                post_id=post_id,
                share_user_id=user_id,
                user_id=recipient_id,
            )
        )
        shared_count += 1
        create_notification(
            db=db,
            recipient_id=recipient_id,
            actor_id=user_id,
            type="post_share",
            post_id=post_id,
            message=payload.message or "Shared a post with you",
        )

    db.commit()
    return {
        "post_id": post_id,
        "shared_count": shared_count,
        "message": "Post shared",
    }
