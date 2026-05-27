from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from core.enumeration import BookingStatus
from models.booking.booking import Booking
from models.profile.insights import SalonInsightEvent
from models.profile.salon import Salon, SalonFollower, SalonServicePrice
from models.saved import SavedService
from service.auth.permissions import ROLE_SALON_OWNER, UserPrincipal


PROFILE_VIEW = "profile_view"
SERVICE_TAP = "service_tap"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_salon_profile_view(*, db: Session, salon_id: str, user_id: str | None) -> None:
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon or user_id == salon.user_id:
        return

    event = SalonInsightEvent(
        salon_id=salon_id,
        user_id=user_id,
        event_type=PROFILE_VIEW,
    )
    db.add(event)
    db.commit()


def record_salon_service_tap(
    *,
    db: Session,
    salon_id: str,
    salon_service_price_id: str,
    user_id: str | None,
) -> dict:
    service_price = (
        db.query(SalonServicePrice)
        .filter(
            SalonServicePrice.id == salon_service_price_id,
            SalonServicePrice.salon_id == salon_id,
        )
        .first()
    )
    if not service_price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon service not found")

    event = SalonInsightEvent(
        salon_id=salon_id,
        user_id=user_id,
        event_type=SERVICE_TAP,
        target_id=salon_service_price_id,
    )
    db.add(event)
    db.commit()
    return {"success": True}


def get_profile_insights(*, db: Session, principal: UserPrincipal) -> dict:
    if principal.role == ROLE_SALON_OWNER:
        salon = db.query(Salon).filter(Salon.user_id == principal.user_id).first()
        if not salon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")
        return _salon_insights(db=db, salon_id=salon.id)

    return _customer_insights(db=db, user_id=principal.user_id)


def _customer_insights(*, db: Session, user_id: str) -> dict:
    saved_styles_count = (
        db.query(func.count(SavedService.id))
        .filter(SavedService.user_id == user_id)
        .scalar()
        or 0
    )
    followed_salons_count = (
        db.query(func.count(SalonFollower.id))
        .filter(SalonFollower.user_id == user_id)
        .scalar()
        or 0
    )
    recent_categories = (
        db.query(
            Booking.service_name_snapshot.label("name"),
            func.count(Booking.id).label("count"),
        )
        .filter(Booking.customer_id == user_id)
        .filter(Booking.service_name_snapshot.isnot(None))
        .group_by(Booking.service_name_snapshot)
        .order_by(func.max(Booking.created_at).desc())
        .limit(5)
        .all()
    )

    return {
        "role": "customer",
        "customer": {
            "saved_styles_count": int(saved_styles_count),
            "followed_salons_count": int(followed_salons_count),
            "recent_booking_categories": [
                {"name": row.name, "count": int(row.count)} for row in recent_categories
            ],
        },
        "salon": None,
    }


def _salon_insights(*, db: Session, salon_id: str) -> dict:
    now = _now()
    last_30_days = now - timedelta(days=30)
    previous_30_days = now - timedelta(days=60)

    profile_views = _event_count(db=db, salon_id=salon_id, event_type=PROFILE_VIEW)
    service_taps = _event_count(db=db, salon_id=salon_id, event_type=SERVICE_TAP)
    total_bookings = (
        db.query(func.count(Booking.id))
        .filter(Booking.salon_id == salon_id)
        .scalar()
        or 0
    )
    returning_customers = (
        db.query(func.count())
        .select_from(
            db.query(Booking.customer_id)
            .filter(
                Booking.salon_id == salon_id,
                Booking.status == BookingStatus.COMPLETED,
            )
            .group_by(Booking.customer_id)
            .having(func.count(Booking.id) >= 2)
            .subquery()
        )
        .scalar()
        or 0
    )
    total_followers = (
        db.query(func.count(SalonFollower.id))
        .filter(SalonFollower.salon_id == salon_id)
        .scalar()
        or 0
    )
    followers_last_30_days = (
        db.query(func.count(SalonFollower.id))
        .filter(
            SalonFollower.salon_id == salon_id,
            SalonFollower.created_at >= last_30_days,
        )
        .scalar()
        or 0
    )
    followers_previous_30_days = (
        db.query(func.count(SalonFollower.id))
        .filter(
            SalonFollower.salon_id == salon_id,
            SalonFollower.created_at >= previous_30_days,
            SalonFollower.created_at < last_30_days,
        )
        .scalar()
        or 0
    )
    unique_profile_viewers = (
        db.query(func.count(distinct(SalonInsightEvent.user_id)))
        .filter(
            SalonInsightEvent.salon_id == salon_id,
            SalonInsightEvent.event_type == PROFILE_VIEW,
            SalonInsightEvent.user_id.isnot(None),
        )
        .scalar()
        or 0
    )

    return {
        "role": "salon",
        "customer": None,
        "salon": {
            "profile_views": int(profile_views),
            "unique_profile_viewers": int(unique_profile_viewers),
            "service_taps": int(service_taps),
            "booking_conversion_rate": round((total_bookings / service_taps) * 100, 1)
            if service_taps
            else 0.0,
            "returning_customers": int(returning_customers),
            "follower_growth": {
                "total_followers": int(total_followers),
                "last_30_days": int(followers_last_30_days),
                "previous_30_days": int(followers_previous_30_days),
                "delta": int(followers_last_30_days - followers_previous_30_days),
            },
        },
    }


def _event_count(*, db: Session, salon_id: str, event_type: str) -> int:
    return int(
        db.query(func.count(SalonInsightEvent.id))
        .filter(
            SalonInsightEvent.salon_id == salon_id,
            SalonInsightEvent.event_type == event_type,
        )
        .scalar()
        or 0
    )
