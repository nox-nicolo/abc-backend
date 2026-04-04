from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.enumeration import PostStatus
from models.posts.posts import Post


def delete_post_(*, post_id: str, user_id: str, db: Session):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your post")

    post.status = PostStatus.DELETED
    db.commit()
    return {"detail": "Post deleted"}
