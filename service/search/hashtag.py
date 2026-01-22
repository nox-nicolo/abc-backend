from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.enumeration import PostStatus, ImageURL
from models.posts.posts import Hashtag, Post, PostHashtag


IMAGE_URL = ImageURL.POSTS_URL.value


def _parse_cursor(cursor: Optional[str]) -> Optional[datetime]:
    if not cursor:
        return None
    try:
        return datetime.fromisoformat(cursor)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor format",
        )


async def get_hashtag_grid_(
    hashtag_id: str,
    db: Session,
    cursor: Optional[str],
    limit: int,
    user: str,
) -> Dict[str, Any]:

    cursor_dt = _parse_cursor(cursor)

    hashtag = (
        db.query(Hashtag)
        .filter(Hashtag.id == hashtag_id)
        .first()
    )

    if not hashtag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hashtag not found",
        )

    
    post_count = (
        db.query(func.count(PostHashtag.id))
        .filter(PostHashtag.hashtag_id == hashtag_id)
        .scalar()
        or 0
    )

    query = (
        db.query(Post)
        .join(PostHashtag, PostHashtag.post_id == Post.id)
        .filter(
            PostHashtag.hashtag_id == hashtag_id,
            Post.status == PostStatus.PUBLISHED.name,
        )
        .order_by(Post.created_at.desc())
    )

    if cursor_dt:
        query = query.filter(Post.created_at < cursor_dt)

    posts: List[Post] = query.limit(limit).all()

    items: List[Dict[str, Any]] = []

    for post in posts:
        if not post.media_items:
            continue

        media = post.media_items[0]

        items.append(
            {
                "post_id": post.id,
                "image": {
                    "url": f"{IMAGE_URL}{media.media_url}",
                },
            }
        )

    return {
        "hashtag": {
            "name": hashtag.name,
            "post_count": post_count,
            "is_trending": post_count >= 1000,
        },
        "posts": items,
        "cursor": posts[-1].created_at.isoformat() if posts else None,
    }
