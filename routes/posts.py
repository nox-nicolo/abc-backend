"""Provides the Posts API route module for the backend application."""

from datetime import datetime
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.enumeration import PostCollectionType
from core.rate_limit import enforce_rate_limit
from models.posts.posts import Hashtag
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.posts.create_post import CreatePostPayload, PostSettingsSchema
from pydantic_schemas.posts.get_post import PostLikeSchema
from pydantic_schemas.posts.comment import (
    CommentCreateRequest,
    CommentItem,
    CommentListResponse,
    CommentLikeResponse,
)
from pydantic_schemas.posts.reaction import (
    PostReactionRequest,
    PostReactionResponse,
    PostShareRequest,
    PostShareResponse,
)
from pydantic_schemas.posts.single_post import SinglePostResponse
from routes.post_router_helper import FormPostData
from service.auth.JWT.oauth2 import get_current_user
from service.posts.comment_post import (
    create_comment,
    delete_comment,
    list_comments,
    toggle_comment_like,
)
from service.posts.create_post import create_post_
from service.posts.get_post import (
    get_posts_,
    get_other_posts_,
    get_profile_posts_,
    get_single_post_view_,
)
from service.posts.delete_post import delete_post_
from service.posts.like_post import toggle_like
from service.posts.pin_post import toggle_pin_
from service.posts.reaction import reaction_state, set_reaction
from service.posts.repost import repost_, share_post_to_users
from service.posts.save_post import toggle_bookmark
from service.posts.update_post import update_post_

posts = APIRouter(prefix="/posts", tags=["Posts"])




@posts.post("/", status_code=201)
async def create_post(
    form: FormPostData = Depends(),
    media: Optional[List[UploadFile]] = File(None),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings_dict = (
        json.loads(form.settings)
        if isinstance(form.settings, str)
        else form.settings
    )

    settings_model = PostSettingsSchema(**settings_dict)

    payload = CreatePostPayload(
        post_type=form.post_type,
        category=form.category,
        caption=form.caption,
        hashtags=form.hashtags,
        tagged=form.tagged,
        media=None,              
        settings=settings_model, 
        status=form.status,
    )

    return await create_post_(
        user_id=current_user.user_id,
        post=payload,
        files=media,
        db=db,
        media_metadata=form.media_metadata,
    )



# ---------------------------------------------------
# Timeline collections
# ---------------------------------------------------
@posts.get("")
async def get_posts_collection(
    option: PostCollectionType = Query(PostCollectionType.feed),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
):
    return await get_posts_(
        user_id=current_user.user_id,
        option=option,
        db=db,
        cursor=cursor,
        limit=limit,
    )


# -------------------------------------------------------
#           GEt Single Post
# -------------------------------------------------------
@posts.get(
    "/{post_id}", response_model=SinglePostResponse,)
async def get_single_post(
    post_id: str,
    other_cursor: Optional[datetime] = Query(None),
    viewer_city: Optional[str] = Query(None),
    viewer_country: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Single Post View (Authenticated)

    Includes:
    - Post data
    - Service context
    - Stylists
    - Reviews
    - Similar results
    - Sponsored salons

    Booking itself is handled by a separate route.
    """

    post_view = await get_single_post_view_(
        db=db,
        post_id=post_id,
        current_user=current_user,
        other_cursor=other_cursor,
        viewer_city=viewer_city,
        viewer_country=viewer_country,
    )

    if not post_view:
        raise HTTPException(status_code=404, detail="Post not found")

    return post_view

#                   END
# ------------------------------------------------------------------


# ---------------------------------------------------
# Profile posts
# ---------------------------------------------------
@posts.get("/profile/{profile_user_id}/posts")
async def get_profile_posts(
    profile_user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
):
    return await get_profile_posts_(
        viewer_user_id=current_user.user_id,
        profile_user_id=profile_user_id,
        db=db,
        cursor=cursor,
        limit=limit,
    )


# ---------------------------------------------------
# Single post
# ---------------------------------------------------
@posts.get("/hashtags/popular")
def get_popular_hashtags(
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    return [
        {"name": "#braids", "number": 120},
        {"name": "#nails", "number": 98},
        {"name": "#hair", "number": 210},
        {"name": "#makeup", "number": 76},
        {"name": "#skincare", "number": 54},
    ]



@posts.get("/hashtags/search")
def search_hashtags(
    q: str = Query(...),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    return [
        {"name": "#braids", "number": 120},
        {"name": "#braidstyles", "number": 34},
        {"name": "#braiding", "number": 18},
    ]
    




# Single Post tag
# ---------------------------------------------------
# Like / Unlike (Toggle)
# ---------------------------------------------------
@posts.post("/{post_id}/like")
async def like_post(
    post_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        bucket="posts:like",
        limit=60,
        window_seconds=60,
        user_id=current_user.user_id,
    )
    return await toggle_like(
        post_id=post_id,
        user_id=current_user.user_id,
        db=db,
    )


# ---------------------------------------------------
# Delete post
# ---------------------------------------------------
@posts.delete("/{post_id}", status_code=200)
def delete_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_post_(post_id=post_id, user_id=current_user.user_id, db=db)


# ---------------------------------------------------
# Repost / Undo repost (toggle)
# ---------------------------------------------------
@posts.post("/{post_id}/repost", status_code=200)
def repost_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return repost_(post_id=post_id, user_id=current_user.user_id, db=db)


@posts.post("/{post_id}/share", response_model=PostShareResponse, status_code=200)
def share_post(
    post_id: str,
    payload: PostShareRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        bucket="posts:share",
        limit=30,
        window_seconds=60,
        user_id=current_user.user_id,
    )
    return share_post_to_users(
        post_id=post_id,
        user_id=current_user.user_id,
        payload=payload,
        db=db,
    )


@posts.get("/{post_id}/reactions", response_model=PostReactionResponse)
def get_post_reactions(
    post_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return reaction_state(post_id=post_id, user_id=current_user.user_id, db=db)


@posts.post("/{post_id}/reactions", response_model=PostReactionResponse, status_code=200)
def react_to_post(
    post_id: str,
    payload: PostReactionRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        bucket="posts:react",
        limit=60,
        window_seconds=60,
        user_id=current_user.user_id,
    )
    return set_reaction(
        post_id=post_id,
        user_id=current_user.user_id,
        reaction=payload.reaction,
        db=db,
    )


# ---------------------------------------------------
# Pin / Unpin (toggle)
# ---------------------------------------------------
@posts.post("/{post_id}/pin", status_code=200)
def pin_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return toggle_pin_(post_id=post_id, user_id=current_user.user_id, db=db)


# ---------------------------------------------------
# Other posts (cursor pagination for infinite scroll)
# ---------------------------------------------------
@posts.get("/{post_id}/other-posts", status_code=200)
async def get_other_posts(
    post_id: str,
    cursor: Optional[datetime] = Query(None),
    limit: int = Query(10, le=30),
    viewer_city: Optional[str] = Query(None),
    viewer_country: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await get_other_posts_(
        viewer_user_id=current_user.user_id,
        post_id=post_id,
        db=db,
        cursor=cursor,
        limit=limit,
        viewer_city=viewer_city,
        viewer_country=viewer_country,
    )


# ---------------------------------------------------
# Comments
# ---------------------------------------------------
@posts.get(
    "/{post_id}/comments",
    response_model=CommentListResponse,
)
def get_comments(
    post_id: str,
    parent_comment_id: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_comments(
        post_id=post_id,
        viewer_user_id=current_user.user_id,
        db=db,
        parent_comment_id=parent_comment_id,
        cursor=cursor,
        limit=limit,
    )


@posts.post(
    "/{post_id}/comments",
    response_model=CommentItem,
    status_code=201,
)
def post_comment(
    post_id: str,
    payload: CommentCreateRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        bucket="posts:comment",
        limit=20,
        window_seconds=60,
        user_id=current_user.user_id,
    )
    return create_comment(
        post_id=post_id,
        user_id=current_user.user_id,
        payload=payload,
        db=db,
    )


@posts.delete(
    "/{post_id}/comments/{comment_id}",
    status_code=200,
)
def remove_comment(
    post_id: str,
    comment_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_comment(
        post_id=post_id,
        comment_id=comment_id,
        user_id=current_user.user_id,
        db=db,
    )


@posts.post(
    "/{post_id}/comments/{comment_id}/like",
    response_model=CommentLikeResponse,
    status_code=200,
)
def like_comment(
    post_id: str,
    comment_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        bucket="posts:comment-like",
        limit=60,
        window_seconds=60,
        user_id=current_user.user_id,
    )
    return toggle_comment_like(
        post_id=post_id,
        comment_id=comment_id,
        user_id=current_user.user_id,
        db=db,
    )


# ---------------------------------------------------
# Bookmark / Unbookmark (toggle save)
# ---------------------------------------------------
@posts.post("/{post_id}/bookmark", status_code=200)
def bookmark_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return toggle_bookmark(post_id=post_id, user_id=current_user.user_id, db=db)


# ---------------------------------------------------
# Update post caption
# ---------------------------------------------------
@posts.patch("/{post_id}", status_code=200)
def update_post(
    post_id: str,
    caption: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_post_(
        post_id=post_id,
        user_id=current_user.user_id,
        caption=caption,
        db=db,
    )
