

import datetime
import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from core.enumeration import ImageDirectories, ImageURL
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.profile.salon import Salon

# Pictuer Directory
PROFILE_PIC = ImageDirectories.PROFILE_DIR.value
COVER_PIC = ImageDirectories.SALON_COVER_DIR.value

# Picture URL
PROFILE_PIC_URL = ImageURL.PROFILE_URL.value
COVER_PIC_URL = ImageURL.SALON_COVER_URL.value

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".tiff"}

def validate_image(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format",
        )
    return ext

def save_image(file: UploadFile, folder: str) -> str:
    ext = validate_image(file)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(folder, filename)

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filename


# Corrected function to handle full paths for deletion
def delete_old_file(folder: str, filename: str | None):
    if not filename:
        return
    if filename == 'user.png':
        return
    path = os.path.join(folder, filename)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception as e:
            print(f"Error deleting file {path}: {e}")

async def upload_account_media_(
    user_id: str,
    profile_image: UploadFile | None,
    cover_ads: UploadFile | None,
    db: Session,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    salon = db.query(Salon).filter(Salon.user_id == user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    # Get existing data for cleanup later
    old_profile_record = db.query(ProfilePicture).filter(ProfilePicture.user_id == user_id).first()
    old_profile_filename = old_profile_record.file_name if old_profile_record else None
    old_cover_filename = salon.display_ads

    try:
        profile_url = None
        cover_url = None

        # 1. HANDLE PROFILE PICTURE
        if profile_image:
            new_profile_file = save_image(profile_image, PROFILE_PIC)
            
            if old_profile_record:
                # Update existing record instead of creating a new one with a conflicting ID
                old_profile_record.file_name = new_profile_file
                old_profile_record.is_custom = True
                old_profile_record.updated_at = datetime.datetime.now(datetime.timezone.utc)
            else:
                # Create new record if none exists
                new_profile_entry = ProfilePicture(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    file_name=new_profile_file,
                    is_custom=True,
                    uploaded_at=datetime.datetime.now(datetime.timezone.utc),
                    updated_at=datetime.datetime.now(datetime.timezone.utc),
                )
                db.add(new_profile_entry)
            
            profile_url = f"{PROFILE_PIC_URL}{new_profile_file}"

        # 2. HANDLE SALON COVER ADS
        if cover_ads:
            new_cover_file = save_image(cover_ads, COVER_PIC)
            salon.display_ads = new_cover_file
            cover_url = f"{COVER_PIC_URL}{new_cover_file}"

        db.commit()

        # 3. CLEANUP OLD FILES (Only after successful commit)
        if profile_image and old_profile_filename:
            delete_old_file(PROFILE_PIC, old_profile_filename)

        if cover_ads and old_cover_filename:
            delete_old_file(COVER_PIC, old_cover_filename)

        return {
            "profile_picture_url": profile_url,
            "cover_ads_url": cover_url,
            "status": "Successfully Updated" 
        }

    except Exception as e:
        db.rollback()
        # If DB fails, we should ideally delete the "new" files we just saved to disk
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if profile_image:
            await profile_image.close()
        if cover_ads:
            await cover_ads.close()