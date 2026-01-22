from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.enumeration import ImageURL
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User

PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value

async def me_(user_id: str, db: Session = Depends(get_db)):
    # Check if user exists
    user_exist = db.query(User.id).filter(User.id == user_id).first()
    if not user_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Join table to get user data with optional profile picture
    user_data = (
        db.query(
            User.id,
            User.username,
            User.phone,
            User.role,
            ProfilePicture.file_name.label("profile_picture")
        )
        .outerjoin(ProfilePicture, User.id == ProfilePicture.user_id)
        .filter(User.id == user_id)
        .first()
    )

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unexpected error retrieving user data'
        )

    result = dict(user_data._asdict())
    result['profile_picture'] = f"{PROFILE_IMAGE_BASE}{result['profile_picture']}"
    
    return result

    