import uuid
from models.profile.salon import SalonFollower
from sqlalchemy.orm import Session


async def follow_salon(
    *,
    db: Session,
    salon_id: str,
    user_id: str,
):
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
    
