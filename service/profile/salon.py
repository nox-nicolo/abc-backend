from fastapi import HTTPException
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import func

from core.enumeration import ImageURL
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.profile.salon import (
    Followers,
    Rate,
    Salon,
)

PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value
COVER_IMAGE_BASE = ImageURL.SALON_COVER_URL.value
SALON_GALLERY_BASE = ImageURL.SALON_GALLERY_URL.value


async def profile_salon(db: Session, user: str):
    print(user)
    
    # ───────────────── User ─────────────────
    user_db = db.query(User).filter(User.id == user).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    # ───────────────── Profile picture ─────────────────
    profile_picture = (
        db.query(ProfilePicture)
        .filter(ProfilePicture.user_id == user)
        .first()
    )

    display_picture = (
        PROFILE_IMAGE_BASE + profile_picture.file_name
        if profile_picture
        else None
    )

    # ───────────────── Salon (core) ─────────────────
    salon = (
        db.query(Salon)
        .options(
            joinedload(Salon.contacts),
            joinedload(Salon.working_hours),
            joinedload(Salon.location),
            joinedload(Salon.galleries),
        )
        .filter(Salon.user_id == user)
        .first()
    )

    if not salon:
        raise HTTPException(status_code=404, detail="Salon profile not found")
    # ───────────────── Gallery with full URLs ─────────────────
    # We map the gallery items to include the full URL for Flutter
    gallery_data = []
    # Sort galleries by created_at since you mentioned position is insertion-based for now
    sorted_galleries = sorted(salon.galleries, key=lambda x: x.created_at)
    
    for g in sorted_galleries:
        gallery_data.append({
            "id": g.id,
            "file_name": g.file_name,
            "image_url": f"{SALON_GALLERY_BASE}{g.file_name}"
        })
        
    cover_image = (
        f"{COVER_IMAGE_BASE}/{salon.display_ads}"
        if salon.display_ads
        else None
    )

    # ───────────────── Counts ─────────────────
    followers_count = (
        db.query(func.count(Followers.id))
        .filter(Followers.follow_this == salon.id)
        .scalar()
        or 0
    )

    rated_count = (
        db.query(func.count(Rate.id))
        .filter(Rate.salon_id == salon.id)
        .scalar()
        or 0
    )
    # ───────────────── Response ─────────────────
    # Ensure keys match SalonProfileResponse fields exactly
    return {
        "id": salon.id,
        "username": user_db.username,
        "title": salon.title,
        "slogan": salon.slogan,
        "description": salon.description,
        "displayAds": cover_image,         # Matches Pydantic field
        "profileCompletion": salon.profile_completion, # Matches Pydantic field

        "profilePicture": display_picture,

        "location": salon.location, 
        "contacts": salon.contacts, 
        "workingHours": sorted(
            salon.working_hours, key=lambda x: x.day_of_week
        ),
        "gallery": gallery_data, 

        "followers": followers_count,
        "rated": float(rated_count), # Ensure this matches the Optional[float] type
    }