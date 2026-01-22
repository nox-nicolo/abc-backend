from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.profile.salon import Salon
from pydantic_schemas.profile.settings import SalonProfileUpdateRequest


async def update_salon_profile_(
    user_id: str,
    payload: SalonProfileUpdateRequest,
    db: Session,
):
    salon = (
        db.query(Salon)
        .filter(Salon.user_id == user_id)
        .first()
    )

    if not salon:
        raise HTTPException(
            status_code=404,
            detail="Salon not found",
        )

    # PATCH semantics: update only provided fields
    if payload.title is not None:
        salon.title = payload.title.strip()

    if payload.slogan is not None:
        salon.slogan = payload.slogan.strip()

    if payload.description is not None:
        salon.description = payload.description.strip()

    try:
        db.commit()
        db.refresh(salon)

        return {
            "title": salon.title,
            "slogan": salon.slogan,
            "description": salon.description,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update salon profile: {str(e)}",
        )
