from datetime import datetime
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.enumeration import PostCollectionType
from models.posts.posts import Hashtag
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.posts.create_post import CreatePostPayload, PostSettingsSchema
from pydantic_schemas.posts.get_post import PostLikeSchema
from pydantic_schemas.posts.single_post import SinglePostResponse
from routes.post_router_helper import FormPostData
from service.auth.JWT.oauth2 import get_current_user
from service.posts.create_post import create_post_
from service.posts.get_post import (
    get_posts_,
    get_profile_posts_,
    get_single_post_view_,
)
from service.posts.like_post import toggle_like

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
@posts.post("/{post_id}/like", )
async def like_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await toggle_like(
        post_id=post_id,
        user_id=current_user.user_id,
        db=db,
    )
