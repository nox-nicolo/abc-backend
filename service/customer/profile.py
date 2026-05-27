from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.user import User
from models.auth.customer_profile import CustomerProfile
from models.booking.booking import Booking, ServiceReview
from models.profile.salon import Salon, SalonFollower
from models.services.service import UserSelectServices
from pydantic_schemas.customer.profile import CustomerProfileResponse, CustomerProfileUpdate, CustomerStatsSchema


PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"


def _build_profile_url(file_name):
    if not file_name:
        return None
    return f"{PROFILE_IMAGE_BASE}{file_name}"


def get_customer_profile_(user_id: str, db: Session, viewer_user_id: str | None = None) -> CustomerProfileResponse:
    user = (
        db.query(User)
        .options(
            joinedload(User.profile_picture),
            joinedload(User.customer_profile),
            joinedload(User.salon),
        )
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile = user.customer_profile

    # Stats
    following_count = (
        db.query(SalonFollower)
        .filter(SalonFollower.user_id == user_id)
        .count()
    )

    bookings_count = (
        db.query(Booking)
        .filter(Booking.customer_id == user_id)
        .count()
    )

    reviews_count = (
        db.query(ServiceReview)
        .filter(ServiceReview.user_id == user_id)
        .count()
    )

    # Preferred services
    user_services = (
        db.query(UserSelectServices)
        .filter(UserSelectServices.user_id == user_id)
        .first()
    )
    preferred_services = user_services.services if user_services and user_services.services else []

    response = CustomerProfileResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        profile_picture=_build_profile_url(user.profile_picture.file_name if user.profile_picture else None),
        bio=profile.bio if profile else None,
        city=profile.city if profile else None,
        country=profile.country if profile else None,
        gender=profile.gender if profile else None,
        preferred_services=preferred_services,
        stats=CustomerStatsSchema(
            following_count=following_count,
            bookings_count=bookings_count,
            reviews_count=reviews_count,
        ),
        is_salon_owner=user.salon is not None,
    )
    if viewer_user_id is None:
        return response

    from service.account.enforcement import apply_customer_profile_visibility

    return apply_customer_profile_visibility(
        db=db,
        profile=response,
        target_user_id=user_id,
        viewer_user_id=viewer_user_id,
    )


def update_customer_profile_(user_id: str, data: CustomerProfileUpdate, db: Session) -> CustomerProfileResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update name on User if provided
    if data.name is not None:
        user.name = data.name

    # Get or create CustomerProfile
    profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == user_id).first()
    if not profile:
        profile = CustomerProfile(user_id=user_id)
        db.add(profile)

    if data.bio is not None:
        profile.bio = data.bio
    if data.city is not None:
        profile.city = data.city
    if data.country is not None:
        profile.country = data.country
    if data.gender is not None:
        profile.gender = data.gender

    profile.updated_at = datetime.now(timezone.utc)

    db.commit()

    return get_customer_profile_(user_id, db)
