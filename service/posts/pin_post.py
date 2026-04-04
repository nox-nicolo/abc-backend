from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.posts.posts import Post, PostSettings


def toggle_pin_(*, post_id: str, user_id: str, db: Session):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your post")

    settings = db.query(PostSettings).filter(PostSettings.post_id == post_id).first()
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post settings not found")

    settings.is_pinned = not settings.is_pinned
    db.commit()
    return {"pinned": settings.is_pinned}
