import os
import shutil
from uuid import uuid4
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from core.enumeration import ImageDirectories, ImageURL
from models.profile.salon import Salon, SalonGallery

MAX_GALLERY_IMAGES = 10
GALLERY_DIR = ImageDirectories.SALON_GALLERY_DIR.value
GALLERY_URL = ImageURL.SALON_GALLERY_URL.value

def _delete_physical_file(file_name: str):
    path = os.path.join(GALLERY_DIR, file_name)
    if os.path.isfile(path):
        os.remove(path)

async def manage_salon_gallery_(
    db: Session,
    user_id: str,
    files: List[UploadFile] = [],
    delete_ids: List[str] = [],
):
    # 1. Get Salon
    salon = db.query(Salon).filter(Salon.user_id == user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    # 2. Delete Requested Images
    if delete_ids:
        to_delete = db.query(SalonGallery).filter(
            SalonGallery.salon_id == salon.id,
            SalonGallery.id.in_(delete_ids)
        ).all()
        
        for item in to_delete:
            _delete_physical_file(item.file_name)
            db.delete(item)
        db.flush() # Sync state before counting for new uploads

    # 3. Check Capacity
    current_count = db.query(SalonGallery).filter(SalonGallery.salon_id == salon.id).count()
    if current_count + len(files) > MAX_GALLERY_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Limit exceeded. You can only add {MAX_GALLERY_IMAGES - current_count} more images."
        )

    # 4. Save New Uploads
    new_items = []
    os.makedirs(GALLERY_DIR, exist_ok=True)

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        file_name = f"{uuid4()}{ext}"
        path = os.path.join(GALLERY_DIR, file_name)

        try:
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            gallery_item = SalonGallery(
                id=str(uuid4()),
                salon_id=salon.id,
                file_name=file_name
            )
            db.add(gallery_item)
            new_items.append(gallery_item)
        except Exception as e:
            print(f"Error saving file: {e}")

    try:
        db.commit()
        # Return the full updated gallery
        full_gallery = db.query(SalonGallery).filter(SalonGallery.salon_id == salon.id).all()
        
        # Attach URLs for the response
        for item in full_gallery:
            item.image_url = f"{GALLERY_URL}{item.file_name}"
            
        return full_gallery
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update gallery")