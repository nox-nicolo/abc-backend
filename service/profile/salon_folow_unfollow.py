import uuid
from fastapi import HTTPException, status
from models.profile.salon import Salon, SalonFollower
from sqlalchemy.orm import Session
from service.account.enforcement import is_blocked_between


async def follow_salon(
    *,
    db: Session,
    salon_id: str,
    user_id: str,
):
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )

    if salon.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salon owners cannot follow their own salon",
        )
    if is_blocked_between(db, user_id, salon.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This salon cannot be followed",
        )

    exists = (
        db.query(SalonFollower)
        .filter(
            SalonFollower.salon_id == salon_id,
            SalonFollower.user_id == user_id,
        )
        .first()
    )

    if exists:
        return  # idempotent

    follow = SalonFollower(
        id = str(uuid.uuid4()),
        salon_id=salon_id,
        user_id=user_id,
        notifications_enabled=True,
    )

    db.add(follow)
    db.commit()


async def unfollow_salon(
    *,
    db: Session,
    salon_id: str,
    user_id: str,
):
    follow = (
        db.query(SalonFollower)
        .filter(
            SalonFollower.salon_id == salon_id,
            SalonFollower.user_id == user_id,
        )
        .first()
    )

    if not follow:
        return

    db.delete(follow)
    db.commit()
    
