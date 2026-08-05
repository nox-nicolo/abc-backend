"""Provides the Reaction business logic module for posts workflows."""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.posts.posts import Post, PostReaction, PostSettings
from pydantic_schemas.posts.reaction import PostReactionResponse

ALLOWED_REACTIONS = {"love", "wow", "excited", "fire", "beautiful"}


def _reaction_summary(*, db: Session, post_id: str) -> dict[str, int]:
    rows = (
        db.query(PostReaction.reaction, func.count(PostReaction.id))
        .filter(PostReaction.post_id == post_id)
        .group_by(PostReaction.reaction)
        .all()
    )
    return {reaction: count for reaction, count in rows}


def reaction_state(*, db: Session, post_id: str, user_id: str) -> PostReactionResponse:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    settings = db.query(PostSettings).filter(PostSettings.post_id == post_id).first()
    reaction: Optional[PostReaction] = (
        db.query(PostReaction)
        .filter(PostReaction.post_id == post_id, PostReaction.user_id == user_id)
        .first()
    )
    return PostReactionResponse(
        post_id=post_id,
        my_reaction=reaction.reaction if reaction else None,
        reactions=_reaction_summary(db=db, post_id=post_id),
        disabled=bool(settings and settings.disable_reactions),
    )


def set_reaction(
    *,
    db: Session,
    post_id: str,
    user_id: str,
    reaction: str,
) -> PostReactionResponse:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    settings = db.query(PostSettings).filter(PostSettings.post_id == post_id).first()
    if settings and settings.disable_reactions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reactions are disabled for this post",
        )

    normalized = reaction.strip().lower()
    if normalized not in ALLOWED_REACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported reaction")

    existing = (
        db.query(PostReaction)
        .filter(PostReaction.post_id == post_id, PostReaction.user_id == user_id)
        .first()
    )
    if existing and existing.reaction == normalized:
        db.delete(existing)
    elif existing:
        existing.reaction = normalized
    else:
        db.add(
            PostReaction(
                id=str(uuid.uuid4()),
                post_id=post_id,
                user_id=user_id,
                reaction=normalized,
            )
        )

    db.commit()
    return reaction_state(db=db, post_id=post_id, user_id=user_id)
