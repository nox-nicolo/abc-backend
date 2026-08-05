"""Provides the Save Post business logic module for posts workflows."""

import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.posts.posts import Post, PostBoorkmark


def toggle_bookmark(*, post_id: str, user_id: str, db: Session):
    """Toggle bookmark (save) for a post. Returns current saved state."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    bookmark = (
        db.query(PostBoorkmark)
        .filter(
            PostBoorkmark.post_id == post_id,
            PostBoorkmark.user_id == user_id,
        )
        .first()
    )

    if bookmark:
        # Already saved → unsave
        db.delete(bookmark)
        db.commit()
        return {"post_id": post_id, "saved": False}
    else:
        # Not saved → save
        db.add(
            PostBoorkmark(
                id=str(uuid.uuid4()),
                post_id=post_id,
                user_id=user_id,
            )
        )
        db.commit()
        return {"post_id": post_id, "saved": True}
