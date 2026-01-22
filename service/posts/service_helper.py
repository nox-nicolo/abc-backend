# Service Post Helper

from ast import Dict, Set
import os
import shutil
import uuid
from sqlalchemy.orm import Session 
from fastapi import Depends, Form, UploadFile, status, HTTPException, File
from typing import List, Optional

from core.database import get_db
from core.enumeration import ImageDirectories, MediaState, MediaType
from models.auth.user import User
from models.posts.posts import Hashtag, MediaData, PostHashtag, PostMention, PostSettings
from pydantic_schemas.posts.create_post import MediaItemSchema, PostSettingsSchema
from sqlalchemy import func

# -------------------------------------------------------------------
# Image Directory
# -------------------------------------------------------------------
ImageDir = ImageDirectories.POST_DIR.value


# -------------------------------------------------------------------
# Hashtags
# -------------------------------------------------------------------
async def hashtags(post_id: str, tags: List[str], db: Session):
    """
    Ensures unique Hashtag entries exist (one row per hashtag) and creates one 
    PostHashtag relationship for every hashtag found in the input list.

    This normalizes all hashtag names to lowercase for consistency and splits
    any comma-separated input entries into individual tags.
    """

    if not tags:
        return

    # --- CLEAN AND UNIQUE THE INPUT TAGS ---

    # This set will hold every unique, clean tag name in lowercase (e.g., '#food', '#travel')
    cleaned_unique_tag_names: Set[str] = set()
    # This list will hold the final, individual list of tags to create relationships for.
    all_tags_to_relate: List[str] = []

    for tag_item in tags:
        # Split by comma to separate any concatenated hashtags (e.g., "#food,#travel")
        # Strip whitespace and normalize to lowercase for consistency.
        individual_tags = [t.strip().lower() for t in tag_item.split(',') if t.strip()]

        # Add the clean, individual tags to the set for uniqueness checking
        cleaned_unique_tag_names.update(individual_tags)

        # Add the clean tags to the list for relationship creation
        all_tags_to_relate.extend(individual_tags)

    if not cleaned_unique_tag_names:
        return

    # --- Batch Query Existing Tags (case-insensitive) ---

    # Query the DB for any existing tags matching the normalized (lowercased) names
    existing_tags = (
        db.query(Hashtag)
        .filter(func.lower(Hashtag.name).in_(list(cleaned_unique_tag_names)))
        .all()
    )

    # Map existing tag names (normalized to lowercase) to their IDs. This also serves as the initial cache.
    tag_id_cache: Dict[str, str] = {tag.name.lower(): tag.id for tag in existing_tags}

    # --- Identify and Create Missing Hashtag Entries ---

    new_db_objects = []

    for tag_name in cleaned_unique_tag_names:

        # If the tag name is not in the cache (meaning it wasn't in the DB)
        if tag_name not in tag_id_cache:
            # Create a new unique Hashtag row (name already lowercased)
            tag_id = str(uuid.uuid4())
            new_tag = Hashtag(id=tag_id, name=tag_name)

            # Add to the list to be committed
            new_db_objects.append(new_tag)

            # Crucial: Add to cache so it can be looked up for relationships
            tag_id_cache[tag_name] = tag_id

    # --- Create PostHashtag relationships ---

    for tag_name in all_tags_to_relate:
        # The tag_id MUST exist in the cache at this point
        tag_id = tag_id_cache.get(tag_name)

        # Create a PostHashtag relationship for this specific instance
        new_db_objects.append(PostHashtag(
            id=str(uuid.uuid4()),
            post_id=post_id,
            hashtag_id=tag_id
        ))

    db.add_all(new_db_objects)


# -------------------------------------------------------------------
# Mentions
# -------------------------------------------------------------------
async def mentions(post_id: str, mention_usernames: List[str], db: Session):
    
    if not mention_usernames:
        return

    new_mentions = []
    
    for user_id in mention_usernames:
        # Populate the mention table with the provided user ID
        new_mentions.append(PostMention(
            id=str(uuid.uuid4()), 
            post_id=post_id,
            mentioned_user_id=user_id
        ))
        
    # Add all new items to the session
    db.add_all(new_mentions)


# -------------------------------------------------------------------
# Add Post Settings
# -------------------------------------------------------------------
async def post_settings_inserted(post_id, settings: PostSettingsSchema, db: Session):
    
    # Insert post settings into the database for a given post_id 
    setting = PostSettings(
        id = str(uuid.uuid4()), 
        post_id = post_id,
        visibility = settings.visibility,
        allow_comments = settings.enableComments,
        allow_likes = settings.showLikes,
        allow_share = settings.allowSharing,
        is_pinned = settings.pinned,
        location = settings.showLocation,
        age_restriction = settings.ageRestriction,
        disable_reactions = settings.disableReactions,
    )

    # Add to session
    db.add(setting)



# -------------------------------------------------------------------
# Upload Post Media
# -------------------------------------------------------------------
async def upload_media(
    post_id: str, 
    metadata: dict,           # <-- dict
    file: UploadFile,
    db: Session
):
    """
    Handles saving a single media item's file to the filesystem 
    and its metadata to the database.
    """

    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Media file object is missing."
        )

    # Generate unique id for media
    media_data_id = str(uuid.uuid4())

    # Save file
    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    allowed_extensions = [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg", ".heic", ".ico", 
        ".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".mpeg", ".mpg", ".3gp", ".m4v"
    ]
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail="Media format is not supported"
        )

    os.makedirs(ImageDir, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    file_location = os.path.join(ImageDir, unique_filename)

    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"File write failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to save media file to disk."
        )

    # Save metadata in database
    media_save = MediaData(
        id=media_data_id,
        media_type=MediaType(metadata["media_type"]),    # dict style
        media_url=unique_filename,
        post_id=post_id,
        media_state=MediaState(metadata["media_state"]),
        aspect_ratio=metadata.get("aspect_ratio")        # use get() in case it's None
    )

    db.add(media_save)
