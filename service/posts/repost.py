import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.posts.posts import Post, PostShare


def repost_(*, post_id: str, user_id: str, db: Session):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

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
