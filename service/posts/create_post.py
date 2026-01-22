import json
from typing import List, Optional, Union
import uuid
from fastapi import Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session 

from core.database import get_db
from models.auth.user import User
from models.posts.posts import MediaData, Post, PostMention
from models.services.service import SubServices
from pydantic_schemas.posts.create_post import CreatePostPayload

from service.posts.service_helper import hashtags, mentions, post_settings_inserted, upload_media

# -------------------------------------------------------------------
# Create Post 
# -------------------------------------------------------------------

async def create_post_(
    user_id: str,
    post: CreatePostPayload,
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a post with associated metadata such as hashtags, mentions, settings, and media uploads.
    Args:
        user_id (str): ID of the user creating the post.
        post (CreatePostPayload): Payload containing post details.
        files (Optional[List[UploadFile]]): List of media files to be uploaded.
        db (Session): Database session.
    Returns:
        dict: A message indicating successful creation and the post ID.
    Raises:
        HTTPException: If the specified category does not exist or if media count does not match files
    """

    # ---------------------------------------------------------
    # Validate or resolve sub_service_id (category)
    # ---------------------------------------------------------
    is_service = (
        db.query(SubServices)
        .filter(SubServices.id == post.category)
        .first()
    )

    if not is_service:
        # fallback to the "Other" subservice; if it doesn't exist, create it
        is_service = (
            db.query(SubServices)
            .filter(SubServices.name == "Other")
            .first()
        )
        if not is_service:
            is_service = SubServices(name="Other")
            db.add(is_service)
            # ensure the new instance gets an id before using it later
            db.flush()

    # ---------------------------------------------------------
    # Create Post ID
    # ---------------------------------------------------------
    post_id = str(uuid.uuid4())

    # ---------------------------------------------------------
    # Save main Post record
    # ---------------------------------------------------------
    save_post = Post(
        id=post_id,
        user_id=user_id,
        caption_text=post.caption,
        status=post.status,
        sub_service_id=is_service.id,
        # font=post.font  # <-- NEW FIELD 
    )

    db.add(save_post)

    # ---------------------------------------------------------
    # Insert Hashtags
    # ---------------------------------------------------------
    if post.hashtags:
        await hashtags(
            post_id=post_id,
            tags=post.hashtags,
            db=db
        )

    # ---------------------------------------------------------
    # Insert Mentions
    # ---------------------------------------------------------
    if post.tagged:
        await mentions(
            post_id=post_id,
            mention_usernames=post.tagged,
            db=db
        )

    # ---------------------------------------------------------
    # Insert Settings
    # ---------------------------------------------------------
    await post_settings_inserted(
        post_id=post_id,
        settings=post.settings,
        db=db
    )

    # ---------------------------------------------------------
    # Media Upload
    # ---------------------------------------------------------
    if files:
        for file in files:

            # Build metadata
            metadata = {
                "media_type": "image",
                "media_state": "uploaded",
                "aspect_ratio": 1.0,
            }

            await upload_media(
                metadata=metadata,
                file=file,
                post_id=post_id,
                db=db
            )

    # ---------------------------------------------------------
    # Commit DB changes
    # ---------------------------------------------------------
    db.commit()
    db.refresh(save_post)

    return {
        "message": "Post Created Successful",
        "post_id": post_id
    }


# -------------------------------------------------------------------
# Delete post 
# -------------------------------------------------------------------
async def delete_post_(
    post_id: str, 
    user_id: str, 
    db: Session = Depends(get_db), 
):
    # get the post
    del_post = db.query(Post).filter(Post.id == post_id).first()
    
    if not del_post:
        # not possible to have nothing to remove
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, 
            detail = "Post not found!"
        )
        

    # compare the user_id and user_post_id, check if the user belong to the post.
    if del_post.user_id != user_id:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED, 
            detail = "You are not authorized to delete this post"
        )
     
    # Remove the post from the post table and all related metadata
    db.delete(del_post)

    db.commit()
    
    return {
        "detail": f"Post {post_id} successfully removed"
    }
    


# Post analytics
# Book mark
# Comments
# Likes
# reports
# Share
# Views