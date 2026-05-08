from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func

from core.enumeration import BookingStatus, ImageURL
from models.booking.booking import Booking
from models.profile.salon import Salon, SalonLocation, SalonServicePrice
from models.auth.user import User

from models.booking.booking import ServiceReview
from models.services.service import SubServices
from pydantic_schemas.booking.booking import (
    BookingCreate,
    BookingCancel,
    BookingReschedule,
    BookingReviewCreate,
)
from pydantic_schemas.pagination import pagination_meta

from pydantic_schemas.booking.choose_salon import SalonOfferForBooking
from service.booking.helper import _auto_no_show, _now
from service.notification.notification import create_notification


salon_url = ImageURL.SALON_COVER_URL.value


# ---------------------------------------------------------
# Create booking
# ---------------------------------------------------------

async def create_booking_service(
    *,
    db: Session,
    payload: BookingCreate,
    user_id: str,
) -> Booking:

    # validate user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User not found",
        )

    # Lock the offering row for the duration of this transaction so two
    # concurrent bookings on the same slot serialize instead of both passing
    # the overlap check.
    offering = (
        db.query(SalonServicePrice)
        .filter(SalonServicePrice.id == payload.salon_service_price_id)
        .with_for_update()
        .first()
    )
    if not offering:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Service offering not found",
        )

    if payload.start_at <= _now():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking start time must be in the future",
        )

    if offering.price_min is None or offering.duration_minutes is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Service price or duration not configured",
        )

    end_at = payload.start_at + timedelta(minutes=offering.duration_minutes)

    capacity = offering.concurrent_capacity or 1
    if _has_overlap(db, offering.id, payload.start_at, end_at, capacity):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This time slot is fully booked, please choose another time",
        )

    booking = Booking(
        customer_id=user_id,
        salon_id=offering.salon_id,
        salon_service_price_id=offering.id,

        start_at=payload.start_at,
        end_at=end_at,

        status=BookingStatus.PENDING,

        # snapshots (agreement)
        service_name_snapshot=(
            offering.sub_service.name
            if offering.sub_service else None
        ),
        price_snapshot=offering.price_min,
        currency_snapshot=offering.currency or "TZS",
        duration_minutes_snapshot=offering.duration_minutes,

        note=payload.note,
    )

    db.add(booking)
    db.flush()

    # Notify salon owner that a new booking came in.
    salon = db.query(Salon).filter(Salon.id == offering.salon_id).first()
    if salon:
        create_notification(
            db=db,
            recipient_id=salon.user_id,
            actor_id=user_id,
            type="booking_new",
            booking_id=booking.id,
            commit=False,
        )

    db.commit()
    db.refresh(booking)

    return booking


# ---------------------------------------------------------
# Get user bookings
# ---------------------------------------------------------

async def get_user_bookings_service(
    *,
    db: Session,
    user_id: str,
    status: Optional[BookingStatus],
    upcoming: Optional[bool],
    limit: int,
    offset: int,
) -> dict:

    query = db.query(Booking).filter(Booking.customer_id == user_id)

    if status:
        query = query.filter(Booking.status == status)

    if upcoming is True:
        query = query.filter(Booking.start_at >= _now())
    elif upcoming is False:
        query = query.filter(Booking.start_at < _now())

    total = query.count()
    bookings = (
        query.order_by(Booking.start_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    for booking in bookings:
        _auto_no_show(booking)

    db.commit()
    return {
        "items": bookings,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


# ---------------------------------------------------------
# Get single booking (user or salon)
# ---------------------------------------------------------

async def get_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> Booking:

    booking = (
        db.query(Booking)
        .options(joinedload(Booking.salon))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Booking not found",
        )

    if booking.customer_id != user_id and booking.salon.user_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Access denied",
        )

    _auto_no_show(booking)
    db.commit()

    return booking


# ---------------------------------------------------------
# Cancel booking (user)
# ---------------------------------------------------------

async def cancel_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
    payload: BookingCancel,
) -> Booking:

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Booking not found",
        )

    if booking.customer_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Not your booking",
        )

    if booking.status not in (
        BookingStatus.PENDING,
        BookingStatus.CONFIRMED,
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking cannot be cancelled",
        )

    if booking.start_at <= _now():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Too late to cancel booking",
        )

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_by = "user"
    booking.cancel_reason = payload.reason

    # Notify salon owner that the customer cancelled.
    salon = db.query(Salon).filter(Salon.id == booking.salon_id).first()
    if salon:
        create_notification(
            db=db,
            recipient_id=salon.user_id,
            actor_id=user_id,
            type="booking_cancelled",
            booking_id=booking.id,
            commit=False,
        )

    db.commit()
    db.refresh(booking)

    return booking


# ---------------------------------------------------------
# Get salon bookings
# ---------------------------------------------------------

async def get_salon_bookings_service(
    *,
    db: Session,
    user_id: str,
    status: Optional[BookingStatus],
    upcoming: Optional[bool],
    date: Optional[str],
    limit: int,
    offset: int,
) -> dict:

    salon = db.query(Salon).filter(Salon.user_id == user_id).first()
    if not salon:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Salon not found",
        )

    query = db.query(Booking).filter(Booking.salon_id == salon.id)

    if status:
        query = query.filter(Booking.status == status)

    if upcoming is True:
        query = query.filter(Booking.start_at >= _now())
    elif upcoming is False:
        query = query.filter(Booking.start_at < _now())

    if date:
        try:
            day = datetime.fromisoformat(date).date()
            start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
            end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)

            query = query.filter(
                and_(
                    Booking.start_at >= start,
                    Booking.start_at <= end,
                )
            )
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Invalid date format (expected YYYY-MM-DD)",
            )

    total = query.count()
    bookings = (
        query.order_by(Booking.start_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    for booking in bookings:
        _auto_no_show(booking)

    db.commit()
    return {
        "items": bookings,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


# ---------------------------------------------------------
# Confirm booking (salon)
# ---------------------------------------------------------

async def confirm_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> Booking:

    booking = db.query(Booking).options(
        joinedload(Booking.customer) 
    ).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Booking not found",
        )

    if booking.salon.user_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Not your salon",
        )

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking cannot be confirmed",
        )

    booking.status = BookingStatus.CONFIRMED
    booking.confirmed_at = _now()

    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_confirmed",
        booking_id=booking.id,
        commit=False,
    )

    db.commit()
    db.refresh(booking)

    return booking


# ---------------------------------------------------------
# Reject booking (salon)
# ---------------------------------------------------------

async def reject_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> Booking:

    booking = (
        db.query(Booking)
        .options(joinedload(Booking.salon))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Booking not found",
        )

    if booking.salon.user_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Not your salon",
        )

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking cannot be rejected",
        )

    booking.status = BookingStatus.REJECTED

    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_rejected",
        booking_id=booking.id,
        commit=False,
    )

    db.commit()
    db.refresh(booking)

    return booking


# ---------------------------------------------------------
# Complete booking (salon)
# ---------------------------------------------------------

async def complete_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> Booking:

    booking = (
        db.query(Booking)
        .options(joinedload(Booking.salon))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Booking not found",
        )

    if booking.salon.user_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Not your salon",
        )

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking cannot be completed",
        )

    if booking.start_at > _now():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking has not started yet",
        )

    booking.status = BookingStatus.COMPLETED
    booking.completed_at = _now()

    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_completed",
        booking_id=booking.id,
        commit=False,
    )

    db.commit()
    db.refresh(booking)

    return booking






def _has_overlap(
    db: Session,
    salon_service_price_id: str,
    start_at: datetime,
    end_at: datetime,
    capacity: int = 1,
    exclude_booking_id: str = None,
) -> bool:
    """Return True when the number of overlapping bookings for this service slot meets or exceeds capacity."""
    count_q = db.query(func.count(Booking.id)).filter(
        Booking.salon_service_price_id == salon_service_price_id,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        Booking.start_at < end_at,
        Booking.end_at > start_at,
    )
    if exclude_booking_id:
        count_q = count_q.filter(Booking.id != exclude_booking_id)
    return count_q.scalar() >= capacity


# ---------------------------------------------------------
# Reschedule booking (customer)
# ---------------------------------------------------------

async def reschedule_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
    payload: BookingReschedule,
) -> Booking:

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if booking.customer_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")

    if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking cannot be rescheduled")

    if booking.start_at <= _now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too late to reschedule this booking")

    if payload.start_at <= _now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New start time must be in the future")

    new_end_at = payload.start_at + timedelta(minutes=booking.duration_minutes_snapshot)

    offering = db.query(SalonServicePrice).filter(SalonServicePrice.id == booking.salon_service_price_id).first()
    capacity = (offering.concurrent_capacity or 1) if offering else 1
    if _has_overlap(db, booking.salon_service_price_id, payload.start_at, new_end_at, capacity, exclude_booking_id=booking_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "This time slot is fully booked")

    booking.start_at = payload.start_at
    booking.end_at = new_end_at
    booking.status = BookingStatus.PENDING  # reset to pending so salon re-confirms

    salon = db.query(Salon).filter(Salon.id == booking.salon_id).first()
    if salon:
        create_notification(
            db=db,
            recipient_id=salon.user_id,
            actor_id=user_id,
            type="booking_rescheduled",
            booking_id=booking.id,
            commit=False,
        )

    db.commit()
    db.refresh(booking)
    return booking


# ---------------------------------------------------------
# Leave a review (customer)
# ---------------------------------------------------------

async def create_review_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
    payload: BookingReviewCreate,
) -> ServiceReview:

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if booking.customer_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")

    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can only review a completed booking")

    existing = db.query(ServiceReview).filter(ServiceReview.booking_id == booking_id).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already reviewed this booking")

    review = ServiceReview(
        booking_id=booking_id,
        user_id=user_id,
        salon_id=booking.salon_id,
        salon_service_price_id=booking.salon_service_price_id,
        rating=payload.rating,
        comment=payload.comment,
    )

    db.add(review)
    db.commit()
    db.refresh(review)
    return review


async def get_salons_for_style(
    *,
    db: Session,
    sub_service_id: str,
    limit: int,
    offset: int,
) -> dict:
    """
    Fetch salons offering a given sub service,
    including price and duration.
    """

    query = (
        db.query(
            SalonServicePrice.id.label("salon_service_price_id"),

            Salon.id.label("salon_id"),
            Salon.title.label("salon_name"),
            (SalonLocation.street + " " + SalonLocation.city + ", " + SalonLocation.country).label("salon_city"),
            Salon.display_ads.label("salon_image"),

            SubServices.id.label("sub_service_id"),
            SubServices.name.label("sub_service_name"),

            # FIX HERE
            SalonServicePrice.price_max.label("price"),
            SalonServicePrice.currency,
            SalonServicePrice.duration_minutes,
        )
        .join(SubServices, SubServices.id == SalonServicePrice.sub_service_id)
        .join(Salon, Salon.id == SalonServicePrice.salon_id)
        .filter(SalonServicePrice.sub_service_id == sub_service_id)
        # .filter(SalonServicePrice.is_active.is_(True))
        .order_by(SalonServicePrice.price_max.asc())
    )
    total = query.count()
    rows = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = [
        SalonOfferForBooking(
            salon_service_price_id=row.salon_service_price_id,

            salon_id=row.salon_id,
            salon_name=row.salon_name,
            salon_city=row.salon_city,
            salon_image= salon_url + row.salon_image if row.salon_image else None,

            sub_service_id=row.sub_service_id,
            sub_service_name=row.sub_service_name,

            price=row.price,
            currency=row.currency,
            duration_minutes=row.duration_minutes,
        )
        for row in rows
    ]

    return {
        "results": results,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }
