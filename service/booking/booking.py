from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from core.enumeration import BookingStatus
from models.booking.booking import Booking
from models.profile.salon import Salon, SalonServicePrice
from models.auth.user import User

from models.services.service import SubServices
from pydantic_schemas.booking.booking import (
    BookingCreate,
    BookingCancel,
)

from pydantic_schemas.booking.choose_salon import SalonOfferForBooking
from service.booking.helper import _auto_no_show, _now


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

    # validate salon service price (bookable unit)
    offering = (
        db.query(SalonServicePrice)
        .filter(SalonServicePrice.id == payload.salon_service_price_id)
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

    end_at = payload.start_at + timedelta(
        minutes=offering.duration_minutes
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
) -> List[Booking]:

    query = db.query(Booking).filter(Booking.customer_id == user_id)

    if status:
        query = query.filter(Booking.status == status)

    if upcoming is True:
        query = query.filter(Booking.start_at >= _now())
    elif upcoming is False:
        query = query.filter(Booking.start_at < _now())

    bookings = query.order_by(Booking.start_at.desc()).all()

    for booking in bookings:
        _auto_no_show(booking)

    db.commit()
    return bookings


# ---------------------------------------------------------
# Get single booking (user or salon)
# ---------------------------------------------------------

async def get_booking_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> Booking:

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
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
) -> List[Booking]:

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

    bookings = query.order_by(Booking.start_at.asc()).all()

    for booking in bookings:
        print(booking.cancel_reason)
        _auto_no_show(booking)

    db.commit()
    return bookings


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
    print(booking.customer.name)  # Accessing the username of the customer

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

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
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

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
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

    db.commit()
    db.refresh(booking)

    return booking






async def get_salons_for_style(
    *,
    db: Session,
    sub_service_id: str,
) -> list[SalonOfferForBooking]:
    """
    Fetch salons offering a given sub service,
    including price and duration.
    """

    rows = (
        db.query(
            SalonServicePrice.id.label("salon_service_price_id"),

            Salon.id.label("salon_id"),
            Salon.title.label("salon_name"),
            Salon.address.label("salon_city"),
            Salon.display_ads.label("salon_image"),

            SubServices.id.label("sub_service_id"),
            SubServices.name.label("sub_service_name"),

            # ✅ FIX HERE
            SalonServicePrice.price_max.label("price"),
            SalonServicePrice.currency,
            SalonServicePrice.duration_minutes,
        )
        .join(SubServices, SubServices.id == SalonServicePrice.sub_service_id)
        .join(Salon, Salon.id == SalonServicePrice.salon_id)
        .filter(SalonServicePrice.sub_service_id == sub_service_id)
        # .filter(SalonServicePrice.is_active.is_(True))
        .order_by(SalonServicePrice.price_max.asc())
        .all()
    )

    return [
        SalonOfferForBooking(
            salon_service_price_id=row.salon_service_price_id,

            salon_id=row.salon_id,
            salon_name=row.salon_name,
            salon_city=row.salon_city,
            salon_image=row.salon_image,

            sub_service_id=row.sub_service_id,
            sub_service_name=row.sub_service_name,

            price=row.price,
            currency=row.currency,
            duration_minutes=row.duration_minutes,
        )
        for row in rows
    ]
