"""Provides the Booking business logic module for the backend application."""

from datetime import date as DateType, datetime, time, timezone, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, case, func, or_, text

from core.enumeration import BookingStatus, ImageURL, ServiceCreatedStatus
from models.booking.booking import Booking, BookingEvent
from models.profile.salon import (
    Salon,
    SalonAvailabilityOverride,
    SalonLocation,
    SalonServicePrice,
    SalonStylist,
    SalonWorkingHour,
    StylistService,
)
from models.auth.user import User

from models.booking.booking import ServiceReview
from models.services.service import SubServices
from pydantic_schemas.booking.booking import (
    BookingEventResponse,
    BookingCreate,
    BookingCancel,
    BookingReschedule,
    BookingReviewCreate,
)
from pydantic_schemas.pagination import pagination_meta

from pydantic_schemas.booking.choose_salon import BookingStylistOption, SalonOfferForBooking
from service.booking.helper import (
    _auto_expire_pending,
    _auto_no_show,
    _is_future,
    _is_past_or_now,
    _now,
)
from models.profile.notification_preferences import UserNotificationPreference
from service.chat import create_booking_chat_event, create_booking_confirmed_chat_event
from service.notification.booking_ai import (
    BookingNotificationContext,
    booking_link,
    generate_booking_confirmation_message,
)
from service.notification.notification import create_notification
from service.account.enforcement import is_blocked_between, salon_booking_rules_for_salon


salon_url = ImageURL.SALON_COVER_URL.value
profile_url = ImageURL.PROFILE_URL.value
SALON_TIMEZONE = ZoneInfo("Africa/Dar_es_Salaam")
MIN_BOOKING_LEAD_MINUTES = 15
ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)
BOOKING_TRANSITIONS = {
    BookingStatus.PENDING: {
        BookingStatus.CONFIRMED,
        BookingStatus.REJECTED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.CONFIRMED: {
        BookingStatus.COMPLETED,
        BookingStatus.CANCELLED,
        BookingStatus.NO_SHOW,
    },
}


def expire_pending_bookings_for_scope(
    db: Session,
    *,
    customer_id: Optional[str] = None,
    salon_id: Optional[str] = None,
) -> int:
    query = (
        db.query(Booking)
        .options(joinedload(Booking.customer), joinedload(Booking.salon))
        .filter(
            Booking.status == BookingStatus.PENDING,
            Booking.start_at <= _now(),
        )
    )
    if customer_id is not None:
        query = query.filter(Booking.customer_id == customer_id)
    if salon_id is not None:
        query = query.filter(Booking.salon_id == salon_id)

    expired = 0
    for booking in query.all():
        if _auto_expire_pending(booking, db=db):
            expired += 1
    return expired


def mark_no_show_bookings_for_scope(
    db: Session,
    *,
    customer_id: Optional[str] = None,
    salon_id: Optional[str] = None,
) -> int:
    query = (
        db.query(Booking)
        .filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.end_at < _now(),
        )
    )
    if customer_id is not None:
        query = query.filter(Booking.customer_id == customer_id)
    if salon_id is not None:
        query = query.filter(Booking.salon_id == salon_id)

    marked = 0
    for booking in query.all():
        before = booking.status
        _auto_no_show(booking)
        if booking.status != before:
            marked += 1
    return marked


def _assert_transition(
    booking: Booking,
    target_status: BookingStatus,
    message: str,
) -> None:
    allowed = BOOKING_TRANSITIONS.get(booking.status, set())
    if target_status not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)


def _validate_bookable_offering(offering: SalonServicePrice) -> None:
    if offering.status != ServiceCreatedStatus.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Service offering is not active")
    if offering.price_min is None or offering.price_min < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Service price is not configured")
    if offering.duration_minutes is None or offering.duration_minutes <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Service duration not configured")
    if offering.concurrent_capacity is not None and offering.concurrent_capacity < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Service capacity is not configured")


def _validate_booking_stylist(
    db: Session,
    *,
    stylist_id: Optional[str],
    salon_id: str,
    salon_service_price_id: str,
) -> None:
    if stylist_id is None:
        return

    stylist = (
        db.query(SalonStylist)
        .filter(
            SalonStylist.id == stylist_id,
            SalonStylist.salon_id == salon_id,
            SalonStylist.is_active.is_(True),
        )
        .first()
    )
    if not stylist:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected stylist is not available")

    can_perform_service = (
        db.query(StylistService.id)
        .filter(
            StylistService.stylist_id == stylist_id,
            StylistService.salon_service_price_id == salon_service_price_id,
        )
        .first()
    )
    if not can_perform_service:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected stylist does not offer this service")


def _validate_future_start(start_at: datetime, message: str, minimum_notice_hours: int | None = None) -> None:
    start_at = _aware_utc(start_at)
    if _is_past_or_now(start_at):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)
    lead_delta = (
        timedelta(hours=minimum_notice_hours)
        if minimum_notice_hours is not None
        else timedelta(minutes=MIN_BOOKING_LEAD_MINUTES)
    )
    if start_at < _now() + lead_delta:
        lead_label = (
            f"{minimum_notice_hours} hours"
            if minimum_notice_hours is not None
            else f"{MIN_BOOKING_LEAD_MINUTES} minutes"
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Booking must be at least {lead_label} from now",
        )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _advisory_lock_key(*parts: object) -> str:
    return ":".join(str(part) for part in parts if part is not None)


def _pg_advisory_xact_lock(db: Session, key: str) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": key},
    )


def _lock_booking_slot(
    db: Session,
    *,
    salon_service_price_id: str,
    start_at: datetime,
    stylist_id: Optional[str] = None,
) -> None:
    local_day = _aware_utc(start_at).astimezone(SALON_TIMEZONE).date().isoformat()
    _pg_advisory_xact_lock(
        db,
        _advisory_lock_key("booking", "offering", salon_service_price_id, local_day),
    )
    if stylist_id is not None:
        _pg_advisory_xact_lock(
            db,
            _advisory_lock_key("booking", "stylist", stylist_id, local_day),
        )


def _booking_service_label(booking: Booking) -> str:
    return booking.service_name_snapshot or "your service"


def _booking_salon_label(booking: Booking) -> str:
    return booking.salon.title if booking.salon else "the salon"


def _booking_customer_label(booking: Booking) -> str:
    return booking.customer.name if booking.customer else "The customer"


def _booking_rejected_message(booking: Booking) -> str:
    return (
        f"{_booking_salon_label(booking)} could not accept your booking request "
        f"for {_booking_service_label(booking)}. Please choose another time or try another stylist."
    )


def _booking_customer_cancelled_message(booking: Booking) -> str:
    reason = (booking.cancel_reason or "").strip()
    reason_text = f" Reason: {reason}" if reason else ""
    return (
        f"{_booking_customer_label(booking)} cancelled the booking for "
        f"{_booking_service_label(booking)}.{reason_text}"
    )


def _booking_no_show_message(booking: Booking) -> str:
    return (
        f"{_booking_salon_label(booking)} marked your booking for "
        f"{_booking_service_label(booking)} as no-show. If this looks wrong, contact the salon."
    )


def _status_value(status_value) -> Optional[str]:
    if status_value is None:
        return None
    return getattr(status_value, "value", str(status_value))


def _booking_event_snapshot(booking: Booking) -> dict:
    return {
        "customer_id": booking.customer_id,
        "salon_id": booking.salon_id,
        "salon_service_price_id": booking.salon_service_price_id,
        "stylist_id": booking.stylist_id,
        "start_at": booking.start_at.isoformat() if booking.start_at else None,
        "end_at": booking.end_at.isoformat() if booking.end_at else None,
        "service_name": booking.service_name_snapshot,
    }


def _record_booking_event(
    db: Session,
    *,
    booking: Booking,
    event_type: str,
    actor_id: Optional[str],
    from_status=None,
    to_status=None,
    metadata: Optional[dict] = None,
) -> BookingEvent:
    event_metadata = _booking_event_snapshot(booking)
    if metadata:
        event_metadata.update(metadata)
    event = BookingEvent(
        booking_id=booking.id,
        actor_id=actor_id,
        event_type=event_type,
        from_status=_status_value(from_status),
        to_status=_status_value(to_status if to_status is not None else booking.status),
        event_metadata=event_metadata,
    )
    db.add(event)
    return event


def _busy_stylist_subquery(
    db: Session,
    *,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: str = None,
    buffer_minutes: int = 0,
):
    buffer_delta = timedelta(minutes=max(buffer_minutes or 0, 0))
    query = (
        db.query(Booking.stylist_id.label("stylist_id"))
        .filter(
            Booking.stylist_id.isnot(None),
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.start_at < end_at + buffer_delta,
            Booking.end_at > start_at - buffer_delta,
        )
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.distinct().subquery()


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
    if offering.salon and offering.salon.user_id == user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Salon owners cannot book their own salon",
        )
    salon = offering.salon or db.query(Salon).filter(Salon.id == offering.salon_id).first()
    if salon and is_blocked_between(db, user_id, salon.user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This salon cannot be contacted")

    rules = salon_booking_rules_for_salon(db, offering.salon_id)
    if not rules.allow_customer_notes and (payload.note or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer notes are disabled for this salon")

    _validate_future_start(
        payload.start_at,
        "Booking start time must be in the future",
        rules.minimum_notice_hours,
    )
    _validate_bookable_offering(offering)
    _validate_booking_stylist(
        db,
        stylist_id=payload.stylist_id,
        salon_id=offering.salon_id,
        salon_service_price_id=offering.id,
    )

    end_at = payload.start_at + timedelta(minutes=offering.duration_minutes)

    _ensure_within_availability(
        db=db,
        salon_id=offering.salon_id,
        start_at=payload.start_at,
        end_at=end_at,
    )

    _lock_booking_slot(
        db,
        salon_service_price_id=offering.id,
        stylist_id=payload.stylist_id,
        start_at=payload.start_at,
    )

    capacity = offering.concurrent_capacity or 1
    if _has_overlap(
        db,
        offering.id,
        payload.start_at,
        end_at,
        capacity,
        buffer_minutes=rules.buffer_minutes,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This time slot is fully booked, please choose another time",
        )
    if _has_stylist_overlap(
        db,
        payload.stylist_id,
        payload.start_at,
        end_at,
        buffer_minutes=rules.buffer_minutes,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Selected stylist is already booked at this time",
        )

    booking = Booking(
        customer_id=user_id,
        salon_id=offering.salon_id,
        salon_service_price_id=offering.id,
        stylist_id=payload.stylist_id,

        start_at=payload.start_at,
        end_at=end_at,

        status=BookingStatus.CONFIRMED if rules.auto_confirm else BookingStatus.PENDING,

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
    _record_booking_event(
        db,
        booking=booking,
        event_type="created",
        actor_id=user_id,
        from_status=None,
        to_status=booking.status,
        metadata={"auto_confirmed": bool(rules.auto_confirm)},
    )
    if rules.auto_confirm:
        _record_booking_event(
            db,
            booking=booking,
            event_type="confirmed",
            actor_id=salon.user_id if salon else None,
            from_status=BookingStatus.PENDING,
            to_status=BookingStatus.CONFIRMED,
            metadata={"auto_confirmed": True},
        )

    # Notify salon owner that a new booking came in.
    salon = salon or db.query(Salon).filter(Salon.id == offering.salon_id).first()
    if salon:
        create_notification(
            db=db,
            recipient_id=salon.user_id,
            actor_id=user_id,
            type="booking_new",
            booking_id=booking.id,
            commit=False,
        )

    create_booking_chat_event(db=db, booking=booking, commit=False)

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
    expired = expire_pending_bookings_for_scope(db, customer_id=user_id)
    if expired:
        db.commit()

    query = (
        db.query(Booking)
        .options(
            joinedload(Booking.customer),
            joinedload(Booking.review),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
        .filter(Booking.customer_id == user_id)
    )

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
        _auto_expire_pending(booking, db=db)
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
        .options(
            joinedload(Booking.salon),
            joinedload(Booking.review),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
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

    _auto_expire_pending(booking, db=db)
    _auto_no_show(booking)
    db.commit()

    return booking


async def get_booking_events_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> List[BookingEventResponse]:
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.salon))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.customer_id != user_id and booking.salon.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    events = (
        db.query(BookingEvent)
        .filter(BookingEvent.booking_id == booking_id)
        .order_by(BookingEvent.created_at.asc())
        .all()
    )
    return [BookingEventResponse.model_validate(event) for event in events]


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

    booking = (
        db.query(Booking)
        .options(joinedload(Booking.review))
        .filter(Booking.id == booking_id)
        .first()
    )
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

    _assert_transition(booking, BookingStatus.CANCELLED, "Booking cannot be cancelled")
    if _is_past_or_now(booking.start_at):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Too late to cancel booking",
        )
    rules = salon_booking_rules_for_salon(db, booking.salon_id)
    if _aware_utc(booking.start_at) < _now() + timedelta(hours=rules.cancel_window_hours):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Bookings must be cancelled at least {rules.cancel_window_hours} hours before start time",
        )

    previous_status = booking.status
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_by = "user"
    booking.cancel_reason = payload.reason
    _record_booking_event(
        db,
        booking=booking,
        event_type="cancelled",
        actor_id=user_id,
        from_status=previous_status,
        to_status=BookingStatus.CANCELLED,
        metadata={"reason": payload.reason},
    )

    # Notify salon owner that the customer cancelled.
    salon = db.query(Salon).filter(Salon.id == booking.salon_id).first()
    if salon:
        create_notification(
            db=db,
            recipient_id=salon.user_id,
            actor_id=user_id,
            type="booking_cancelled",
            booking_id=booking.id,
            message=_booking_customer_cancelled_message(booking),
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

    expired = expire_pending_bookings_for_scope(db, salon_id=salon.id)
    if expired:
        db.commit()

    query = (
        db.query(Booking)
        .options(
            joinedload(Booking.customer),
            joinedload(Booking.review),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
        .filter(Booking.salon_id == salon.id)
    )

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
        _auto_expire_pending(booking, db=db)
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
        joinedload(Booking.customer),
        joinedload(Booking.salon),
        joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
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

    if _auto_expire_pending(booking, db=db):
        db.commit()
        db.refresh(booking)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This booking request has expired because the appointment time has passed",
        )

    _assert_transition(booking, BookingStatus.CONFIRMED, "Booking cannot be confirmed")
    if _is_past_or_now(booking.start_at):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too late to confirm booking")

    previous_status = booking.status
    booking.status = BookingStatus.CONFIRMED
    _record_booking_event(
        db,
        booking=booking,
        event_type="confirmed",
        actor_id=user_id,
        from_status=previous_status,
        to_status=BookingStatus.CONFIRMED,
    )

    pref = (
        db.query(UserNotificationPreference)
        .filter(UserNotificationPreference.user_id == booking.customer_id)
        .first()
    )
    reminder_minutes = pref.reminder_lead_minutes if pref else 30
    local_start = booking.start_at.astimezone(timezone(timedelta(hours=3)))
    confirmation = generate_booking_confirmation_message(
        BookingNotificationContext(
            customer_name=booking.customer.name if booking.customer else "there",
            service_type=booking.service_name_snapshot or "your service",
            salon_name=booking.salon.title if booking.salon else "the salon",
            booking_date=local_start.strftime("%A %d %b"),
            booking_time=local_start.strftime("%H:%M"),
            booking_link=booking_link(booking.id),
        ),
        reminder_lead_minutes=reminder_minutes,
    )
    confirmation_message = confirmation["message"]

    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_confirmed",
        booking_id=booking.id,
        message=confirmation_message,
        commit=False,
    )
    create_booking_confirmed_chat_event(
        db=db,
        booking=booking,
        message=confirmation_message,
        salon_user_id=user_id,
        commit=False,
    )

    db.commit()
    db.refresh(booking)

    return booking


async def assign_booking_stylist_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
    stylist_id: Optional[str],
) -> Booking:
    booking = (
        db.query(Booking)
        .options(
            joinedload(Booking.salon),
            joinedload(Booking.salon_service_price),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
        .filter(Booking.id == booking_id)
        .with_for_update()
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if booking.salon.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your salon")

    if booking.status not in ACTIVE_BOOKING_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking cannot be assigned a stylist")

    if _is_past_or_now(booking.end_at):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too late to assign stylist")

    offering = booking.salon_service_price
    if not offering:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service offering not found")

    _validate_bookable_offering(offering)
    _validate_booking_stylist(
        db,
        stylist_id=stylist_id,
        salon_id=booking.salon_id,
        salon_service_price_id=booking.salon_service_price_id,
    )

    rules = salon_booking_rules_for_salon(db, booking.salon_id)
    _lock_booking_slot(
        db,
        salon_service_price_id=booking.salon_service_price_id,
        stylist_id=stylist_id,
        start_at=booking.start_at,
    )

    if _has_stylist_overlap(
        db,
        stylist_id,
        booking.start_at,
        booking.end_at,
        exclude_booking_id=booking.id,
        buffer_minutes=rules.buffer_minutes,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Selected stylist is already booked at this time",
        )

    previous_stylist_id = booking.stylist_id
    booking.stylist_id = stylist_id
    _record_booking_event(
        db,
        booking=booking,
        event_type="stylist_assigned",
        actor_id=user_id,
        from_status=booking.status,
        to_status=booking.status,
        metadata={
            "previous_stylist_id": previous_stylist_id,
            "stylist_id": stylist_id,
        },
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
        .options(
            joinedload(Booking.salon),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
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

    if _auto_expire_pending(booking, db=db):
        db.commit()
        db.refresh(booking)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This booking request has expired because the appointment time has passed",
        )

    _assert_transition(booking, BookingStatus.REJECTED, "Booking cannot be rejected")
    if _is_past_or_now(booking.start_at):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too late to reject booking")

    previous_status = booking.status
    booking.status = BookingStatus.REJECTED
    _record_booking_event(
        db,
        booking=booking,
        event_type="rejected",
        actor_id=user_id,
        from_status=previous_status,
        to_status=BookingStatus.REJECTED,
    )

    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_rejected",
        booking_id=booking.id,
        message=_booking_rejected_message(booking),
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
        .options(
            joinedload(Booking.salon),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
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

    _assert_transition(booking, BookingStatus.COMPLETED, "Booking cannot be completed")
    if _is_future(booking.end_at):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Booking has not ended yet",
        )

    previous_status = booking.status
    booking.status = BookingStatus.COMPLETED
    _record_booking_event(
        db,
        booking=booking,
        event_type="completed",
        actor_id=user_id,
        from_status=previous_status,
        to_status=BookingStatus.COMPLETED,
    )

    service_name = booking.service_name_snapshot or "your service"
    salon_name = booking.salon.title if booking.salon else "the salon"
    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_completed",
        booking_id=booking.id,
        message=(
            f"{salon_name} marked {service_name} as complete. "
            "You can leave an optional review when you are ready."
        ),
        commit=False,
    )

    db.commit()
    db.refresh(booking)

    return booking


async def get_availability_slots_service(
    *,
    db: Session,
    salon_service_price_id: str,
    start_date: DateType | None = None,
    days: int = 14,
    stylist_id: Optional[str] = None,
) -> dict:
    offering = (
        db.query(SalonServicePrice)
        .filter(SalonServicePrice.id == salon_service_price_id)
        .first()
    )
    if not offering:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service offering not found")
    _validate_bookable_offering(offering)
    _validate_booking_stylist(
        db,
        stylist_id=stylist_id,
        salon_id=offering.salon_id,
        salon_service_price_id=offering.id,
    )
    rules = salon_booking_rules_for_salon(db, offering.salon_id)

    days = max(1, min(days, 31))
    today = datetime.now(SALON_TIMEZONE).date()
    first_day = start_date or today
    if first_day < today:
        first_day = today

    items = []
    duration = timedelta(minutes=offering.duration_minutes)
    capacity = offering.concurrent_capacity or 1
    now_utc = _now() + timedelta(hours=rules.minimum_notice_hours)

    for offset in range(days):
        day = first_day + timedelta(days=offset)
        is_open, open_time, close_time, reason = _effective_hours_for_date(
            db=db,
            salon_id=offering.salon_id,
            day=day,
        )
        slots = []
        if is_open and open_time and close_time:
            cursor = datetime.combine(day, open_time, tzinfo=SALON_TIMEZONE)
            close_at = datetime.combine(day, close_time, tzinfo=SALON_TIMEZONE)
            while cursor + duration <= close_at:
                start_utc = cursor.astimezone(timezone.utc)
                end_utc = (cursor + duration).astimezone(timezone.utc)
                if start_utc > now_utc:
                    overlapping = _overlap_count(
                        db,
                        offering.id,
                        start_utc,
                        end_utc,
                        buffer_minutes=rules.buffer_minutes,
                    )
                    remaining = capacity - overlapping
                    stylist_busy = _has_stylist_overlap(
                        db,
                        stylist_id,
                        start_utc,
                        end_utc,
                        buffer_minutes=rules.buffer_minutes,
                    )
                    if remaining > 0 and not stylist_busy:
                        slots.append(
                            {
                                "start_at": start_utc,
                                "end_at": end_utc,
                                "remaining_capacity": remaining,
                            }
                        )
                cursor += timedelta(minutes=rules.slot_interval_minutes)

        items.append(
            {
                "date": day,
                "is_open": bool(is_open),
                "reason": reason,
                "slots": slots,
            }
        )

    return {"items": items}


def _effective_hours_for_date(
    *,
    db: Session,
    salon_id: str,
    day: DateType,
) -> tuple[bool, time | None, time | None, str | None]:
    override = (
        db.query(SalonAvailabilityOverride)
        .filter(
            SalonAvailabilityOverride.salon_id == salon_id,
            SalonAvailabilityOverride.date == day,
        )
        .first()
    )
    if override:
        if override.is_closed:
            return False, None, None, override.reason
        return True, override.open_time, override.close_time, override.reason

    hours = (
        db.query(SalonWorkingHour)
        .filter(
            SalonWorkingHour.salon_id == salon_id,
            SalonWorkingHour.day_of_week == day.weekday(),
        )
        .first()
    )
    if not hours or not hours.is_open:
        return False, None, None, None
    return True, hours.open_time, hours.close_time, None


def _ensure_within_availability(
    *,
    db: Session,
    salon_id: str,
    start_at: datetime,
    end_at: datetime,
) -> None:
    local_start = start_at.astimezone(SALON_TIMEZONE)
    local_end = end_at.astimezone(SALON_TIMEZONE)
    if local_start.date() != local_end.date():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Selected time must finish on the same day",
        )

    is_open, open_time, close_time, _ = _effective_hours_for_date(
        db=db,
        salon_id=salon_id,
        day=local_start.date(),
    )
    if not is_open or not open_time or not close_time:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Salon is closed at this time")

    if local_start.time() < open_time or local_end.time() > close_time:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Selected time is outside salon availability",
        )


def _overlap_count(
    db: Session,
    salon_service_price_id: str,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: str = None,
    buffer_minutes: int = 0,
) -> int:
    buffer_delta = timedelta(minutes=max(buffer_minutes or 0, 0))
    count_q = db.query(func.count(Booking.id)).filter(
        Booking.salon_service_price_id == salon_service_price_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        Booking.start_at < end_at + buffer_delta,
        Booking.end_at > start_at - buffer_delta,
    )
    if exclude_booking_id:
        count_q = count_q.filter(Booking.id != exclude_booking_id)
    return count_q.scalar() or 0


def _stylist_overlap_count(
    db: Session,
    stylist_id: str,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: str = None,
    buffer_minutes: int = 0,
) -> int:
    buffer_delta = timedelta(minutes=max(buffer_minutes or 0, 0))
    count_q = db.query(func.count(Booking.id)).filter(
        Booking.stylist_id == stylist_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        Booking.start_at < end_at + buffer_delta,
        Booking.end_at > start_at - buffer_delta,
    )
    if exclude_booking_id:
        count_q = count_q.filter(Booking.id != exclude_booking_id)
    return count_q.scalar() or 0


def _has_stylist_overlap(
    db: Session,
    stylist_id: Optional[str],
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: str = None,
    buffer_minutes: int = 0,
) -> bool:
    if stylist_id is None:
        return False
    return _stylist_overlap_count(
        db,
        stylist_id,
        start_at,
        end_at,
        exclude_booking_id,
        buffer_minutes,
    ) > 0





def _has_overlap(
    db: Session,
    salon_service_price_id: str,
    start_at: datetime,
    end_at: datetime,
    capacity: int = 1,
    exclude_booking_id: str = None,
    buffer_minutes: int = 0,
) -> bool:
    """Return True when the number of overlapping bookings for this service slot meets or exceeds capacity."""
    return _overlap_count(
        db,
        salon_service_price_id,
        start_at,
        end_at,
        exclude_booking_id,
        buffer_minutes,
    ) >= capacity


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

    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .with_for_update()
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if booking.customer_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")

    if booking.status not in ACTIVE_BOOKING_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking cannot be rescheduled")
    if _is_past_or_now(booking.start_at):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too late to reschedule this booking")

    offering = (
        db.query(SalonServicePrice)
        .filter(SalonServicePrice.id == booking.salon_service_price_id)
        .with_for_update()
        .first()
    )
    if not offering:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service offering not found")
    rules = salon_booking_rules_for_salon(db, booking.salon_id)
    _validate_future_start(
        payload.start_at,
        "New start time must be in the future",
        rules.minimum_notice_hours,
    )

    new_end_at = payload.start_at + timedelta(minutes=booking.duration_minutes_snapshot)

    _validate_bookable_offering(offering)
    _ensure_within_availability(
        db=db,
        salon_id=booking.salon_id,
        start_at=payload.start_at,
        end_at=new_end_at,
    )
    _lock_booking_slot(
        db,
        salon_service_price_id=booking.salon_service_price_id,
        stylist_id=booking.stylist_id,
        start_at=payload.start_at,
    )

    capacity = (offering.concurrent_capacity or 1) if offering else 1
    if _has_overlap(
        db,
        booking.salon_service_price_id,
        payload.start_at,
        new_end_at,
        capacity,
        exclude_booking_id=booking_id,
        buffer_minutes=rules.buffer_minutes,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "This time slot is fully booked")
    if _has_stylist_overlap(
        db,
        booking.stylist_id,
        payload.start_at,
        new_end_at,
        exclude_booking_id=booking_id,
        buffer_minutes=rules.buffer_minutes,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Selected stylist is already booked at this time")

    previous_status = booking.status
    previous_start_at = booking.start_at
    previous_end_at = booking.end_at
    booking.start_at = payload.start_at
    booking.end_at = new_end_at
    booking.status = BookingStatus.PENDING  # reset to pending so salon re-confirms
    _record_booking_event(
        db,
        booking=booking,
        event_type="rescheduled",
        actor_id=user_id,
        from_status=previous_status,
        to_status=BookingStatus.PENDING,
        metadata={
            "previous_start_at": previous_start_at.isoformat() if previous_start_at else None,
            "previous_end_at": previous_end_at.isoformat() if previous_end_at else None,
            "new_start_at": booking.start_at.isoformat() if booking.start_at else None,
            "new_end_at": booking.end_at.isoformat() if booking.end_at else None,
        },
    )

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
# Mark no-show (salon)
# ---------------------------------------------------------

async def mark_no_show_service(
    *,
    db: Session,
    booking_id: str,
    user_id: str,
) -> Booking:
    booking = (
        db.query(Booking)
        .options(
            joinedload(Booking.salon),
            joinedload(Booking.stylist).joinedload(SalonStylist.user).joinedload(User.profile_picture),
        )
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if booking.salon.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your salon")

    _assert_transition(booking, BookingStatus.NO_SHOW, "Booking cannot be marked no-show")
    if _is_future(booking.end_at):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking has not ended yet")

    previous_status = booking.status
    booking.status = BookingStatus.NO_SHOW
    _record_booking_event(
        db,
        booking=booking,
        event_type="no_show",
        actor_id=user_id,
        from_status=previous_status,
        to_status=BookingStatus.NO_SHOW,
    )
    create_notification(
        db=db,
        recipient_id=booking.customer_id,
        actor_id=user_id,
        type="booking_no_show",
        booking_id=booking.id,
        message=_booking_no_show_message(booking),
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

    booking = (
        db.query(Booking)
        .options(joinedload(Booking.salon_service_price))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if booking.customer_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")

    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can only review a completed booking")

    existing = db.query(ServiceReview).filter(ServiceReview.booking_id == booking_id).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already reviewed this booking")

    offering = booking.salon_service_price
    if not offering:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking service is no longer available for review")

    review = ServiceReview(
        booking_id=booking_id,
        user_id=user_id,
        salon_id=booking.salon_id,
        salon_service_price_id=booking.salon_service_price_id,
        service_id=offering.service_id,
        sub_service_id=offering.sub_service_id,
        stylist_id=booking.stylist_id,
        rating=payload.rating,
        comment=payload.comment,
    )

    db.add(review)
    db.flush()
    _record_booking_event(
        db,
        booking=booking,
        event_type="reviewed",
        actor_id=user_id,
        from_status=booking.status,
        to_status=booking.status,
        metadata={"review_id": review.id, "rating": payload.rating},
    )
    db.commit()
    db.refresh(review)
    return review


async def get_salons_for_style(
    *,
    db: Session,
    sub_service_id: str,
    limit: int,
    offset: int,
    current_user_id: str | None = None,
) -> dict:
    """
    Fetch salons offering a given sub service,
    including price and duration.
    """

    query = (
        db.query(
            SalonServicePrice.id.label("salon_service_price_id"),

            Salon.id.label("salon_id"),
            Salon.user_id.label("user_id"),
            Salon.title.label("salon_name"),
            (SalonLocation.street + " " + SalonLocation.city + ", " + SalonLocation.country).label("salon_city"),
            Salon.display_ads.label("salon_image"),

            SubServices.id.label("sub_service_id"),
            SubServices.name.label("sub_service_name"),

            SalonServicePrice.price_min.label("price"),
            SalonServicePrice.currency,
            SalonServicePrice.duration_minutes,
        )
        .join(SubServices, SubServices.id == SalonServicePrice.sub_service_id)
        .join(Salon, Salon.id == SalonServicePrice.salon_id)
        .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
        .filter(SalonServicePrice.sub_service_id == sub_service_id)
        .filter(SalonServicePrice.status == ServiceCreatedStatus.ACTIVE)
        .filter(SalonServicePrice.price_min.isnot(None))
        .filter(SalonServicePrice.price_min >= 0)
        .filter(SalonServicePrice.duration_minutes.isnot(None))
        .filter(SalonServicePrice.duration_minutes > 0)
        .filter(SalonServicePrice.concurrent_capacity >= 1)
        .order_by(SalonServicePrice.price_min.asc())
    )
    total = query.count()
    rows = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        if is_blocked_between(db, current_user_id, row.user_id):
            continue
        results.append(
            SalonOfferForBooking(
                salon_service_price_id=row.salon_service_price_id,

                salon_id=row.salon_id,
                salon_name=row.salon_name,
                salon_city=row.salon_city,
                salon_image=salon_url + row.salon_image if row.salon_image else None,

                sub_service_id=row.sub_service_id,
                sub_service_name=row.sub_service_name,

                price=row.price,
                currency=row.currency,
                duration_minutes=row.duration_minutes,
            )
        )

    return {
        "results": results,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


async def get_booking_stylists_for_offer(
    *,
    db: Session,
    salon_service_price_id: str,
    start_at: Optional[datetime] = None,
    exclude_booking_id: Optional[str] = None,
    limit: int,
    offset: int,
) -> dict:
    offering = (
        db.query(SalonServicePrice)
        .filter(SalonServicePrice.id == salon_service_price_id)
        .first()
    )
    if not offering:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service offering not found")
    _validate_bookable_offering(offering)

    sub_service_rating_sq = (
        db.query(
            ServiceReview.stylist_id.label("stylist_id"),
            func.avg(ServiceReview.rating).label("avg_rating"),
            func.count(ServiceReview.id).label("review_count"),
        )
        .filter(ServiceReview.sub_service_id == offering.sub_service_id)
        .group_by(ServiceReview.stylist_id)
        .subquery()
    )
    service_rating_sq = (
        db.query(
            ServiceReview.stylist_id.label("stylist_id"),
            func.avg(ServiceReview.rating).label("avg_rating"),
            func.count(ServiceReview.id).label("review_count"),
        )
        .filter(ServiceReview.service_id == offering.service_id)
        .group_by(ServiceReview.stylist_id)
        .subquery()
    )

    avg_rating = func.coalesce(
        sub_service_rating_sq.c.avg_rating,
        service_rating_sq.c.avg_rating,
        0,
    ).label("rating")
    review_count = func.coalesce(
        sub_service_rating_sq.c.review_count,
        service_rating_sq.c.review_count,
        0,
    ).label("reviews_count")
    confidence = case(
        (review_count > 20, 1.0),
        else_=review_count / 20.0,
    )
    score = (avg_rating * 0.8 + confidence).label("recommendation_score")

    query = (
        db.query(
            SalonStylist,
            avg_rating,
            review_count,
            score,
        )
        .join(StylistService, StylistService.stylist_id == SalonStylist.id)
        .options(joinedload(SalonStylist.user).joinedload(User.profile_picture))
        .outerjoin(
            sub_service_rating_sq,
            sub_service_rating_sq.c.stylist_id == SalonStylist.id,
        )
        .outerjoin(
            service_rating_sq,
            service_rating_sq.c.stylist_id == SalonStylist.id,
        )
        .filter(
            StylistService.salon_service_price_id == salon_service_price_id,
            SalonStylist.salon_id == offering.salon_id,
            SalonStylist.is_active.is_(True),
        )
    )

    if start_at is not None:
        start_at = _aware_utc(start_at)
        end_at = start_at + timedelta(minutes=offering.duration_minutes)
        rules = salon_booking_rules_for_salon(db, offering.salon_id)
        busy_sq = _busy_stylist_subquery(
            db,
            start_at=start_at,
            end_at=end_at,
            exclude_booking_id=exclude_booking_id,
            buffer_minutes=rules.buffer_minutes,
        )
        query = (
            query.outerjoin(busy_sq, busy_sq.c.stylist_id == SalonStylist.id)
            .filter(busy_sq.c.stylist_id.is_(None))
        )

    total = query.count()
    rows = (
        query
        .order_by(score.desc(), review_count.desc(), SalonStylist.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for index, (stylist, rating, reviews_count, _) in enumerate(rows):
        is_recommended = offset == 0 and index == 0
        rating = round(float(rating or 0), 2)
        reviews_count = int(reviews_count or 0)
        profile_file = (
            stylist.user.profile_picture.file_name
            if stylist.user and stylist.user.profile_picture
            else None
        )
        results.append(
            BookingStylistOption(
                stylist_id=stylist.id,
                user_id=stylist.user_id,
                name=stylist.user.name if stylist.user else (stylist.title or "Stylist"),
                title=stylist.title,
                bio=stylist.bio,
                image=profile_url + profile_file if profile_file else None,
                rating=rating,
                reviews_count=reviews_count,
                is_recommended=is_recommended,
                recommendation_reason=(
                    "Recommended from reviews for this service"
                    if is_recommended and reviews_count > 0
                    else "Available for your selected time"
                    if is_recommended and start_at is not None
                    else None
                ),
            )
        )

    return {
        "results": results,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


def _rating_summary_for_stylist(
    db: Session,
    *,
    stylist_id: str,
    service_id: Optional[str] = None,
    sub_service_id: Optional[str] = None,
) -> dict:
    query = db.query(ServiceReview).filter(ServiceReview.stylist_id == stylist_id)
    if service_id is not None:
        query = query.filter(ServiceReview.service_id == service_id)
    if sub_service_id is not None:
        query = query.filter(ServiceReview.sub_service_id == sub_service_id)
    avg_rating, count = query.with_entities(
        func.avg(ServiceReview.rating),
        func.count(ServiceReview.id),
    ).one()
    return {
        "average": round(float(avg_rating), 2) if avg_rating is not None else 0.0,
        "count": int(count or 0),
    }
