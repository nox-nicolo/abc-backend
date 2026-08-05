"""Provides the Update Post business logic module for posts workflows."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.enumeration import PostStatus
from models.posts.posts import Post


def update_post_(*, post_id: str, user_id: str, caption: str, db: Session):
    """Update a post's caption. Only the post owner can do this."""
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your post")

    if post.status == PostStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.caption_text = caption
    db.commit()
    db.refresh(post)

    return {"detail": "Post updated", "post_id": post.id}
