import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.user import User
from models.posts.posts import Post, PostComment
from pydantic_schemas.posts.comment import (
    CommentAuthor,
    CommentCreateRequest,
    CommentItem,
    CommentListResponse,
)
from service.notification.notification import create_notification


PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"


def _avatar_url(user: User) -> Optional[str]:
    if user.profile_picture and user.profile_picture.file_name:
        return f"{PROFILE_IMAGE_BASE}{user.profile_picture.file_name}"
    return None


def _to_item(
    comment: PostComment,
    viewer_user_id: str,
    reply_counts: dict[str, int],
) -> CommentItem:
    user = comment.user
    return CommentItem(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        author=CommentAuthor(
            id=user.id,
            username=user.username,
            profile_picture=_avatar_url(user),
        ),
        parent_comment_id=comment.comment_id,
        reply_count=reply_counts.get(comment.id, 0),
        created_at=comment.created_at,
        is_mine=comment.user_com == viewer_user_id,
    )


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------
def create_comment(
    *,
    post_id: str,
    user_id: str,
    payload: CommentCreateRequest,
    db: Session,
) -> CommentItem:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    parent: Optional[PostComment] = None
    if payload.parent_comment_id:
        parent = (
            db.query(PostComment)
            .filter(
                PostComment.id == payload.parent_comment_id,
                PostComment.post_id == post_id,
            )
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    comment = PostComment(
        id=str(uuid.uuid4()),
        post_id=post_id,
        user_com=user_id,
        user_rep=payload.parent_comment_id and payload.parent_comment_id or None,
        comment_id=payload.parent_comment_id,
        content=payload.content.strip(),
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    # notifications: reply → parent comment author; top-level → post owner
    if parent:
        create_notification(
            db=db,
            recipient_id=parent.user_com,
            actor_id=user_id,
            type="reply",
            post_id=post_id,
            comment_id=comment.id,
        )
    else:
        create_notification(
            db=db,
            recipient_id=post.user_id,
            actor_id=user_id,
            type="comment",
            post_id=post_id,
            comment_id=comment.id,
        )

    # re-fetch with user for author payload
    comment = (
        db.query(PostComment)
        .options(joinedload(PostComment.user).joinedload(User.profile_picture))
        .filter(PostComment.id == comment.id)
        .first()
    )

    return _to_item(comment, viewer_user_id=user_id, reply_counts={})


# ------------------------------------------------------------------
# LIST (cursor-paginated, top-level or replies)
# ------------------------------------------------------------------
def list_comments(
    *,
    post_id: str,
    viewer_user_id: str,
    db: Session,
    parent_comment_id: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> CommentListResponse:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    cursor_dt: Optional[datetime] = None
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    query = (
        db.query(PostComment)
        .options(joinedload(PostComment.user).joinedload(User.profile_picture))
        .filter(PostComment.post_id == post_id)
    )

    if parent_comment_id is None:
        query = query.filter(PostComment.comment_id.is_(None))
    else:
        query = query.filter(PostComment.comment_id == parent_comment_id)

    if cursor_dt:
        query = query.filter(PostComment.created_at < cursor_dt)

    comments = (
        query.order_by(PostComment.created_at.desc())
        .limit(limit)
        .all()
    )

    reply_counts: dict[str, int] = {}
    if comments and parent_comment_id is None:
        ids = [c.id for c in comments]
        rows = (
            db.query(PostComment.comment_id, func.count(PostComment.id))
            .filter(PostComment.comment_id.in_(ids))
            .group_by(PostComment.comment_id)
            .all()
        )
        reply_counts = {cid: n for cid, n in rows}

    return CommentListResponse(
        items=[
            _to_item(c, viewer_user_id=viewer_user_id, reply_counts=reply_counts)
            for c in comments
        ],
        next_cursor=comments[-1].created_at.isoformat() if comments else None,
    )


# ------------------------------------------------------------------
# DELETE (author only; post owner can remove as moderation)
# ------------------------------------------------------------------
def delete_comment(
    *,
    post_id: str,
    comment_id: str,
    user_id: str,
    db: Session,
) -> dict:
    comment = (
        db.query(PostComment)
        .filter(
            PostComment.id == comment_id,
            PostComment.post_id == post_id,
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    post = db.query(Post).filter(Post.id == post_id).first()
    is_post_owner = post and post.user_id == user_id

    if comment.user_com != user_id and not is_post_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this comment",
        )

    db.delete(comment)
    db.commit()

    return {"comment_id": comment_id, "deleted": True}
