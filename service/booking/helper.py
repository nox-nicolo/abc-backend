# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

from datetime import datetime, timezone

from core.enumeration import BookingStatus
from models.booking.booking import Booking


def _now():
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize DB datetimes before Python-side comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_past_or_now(value: datetime) -> bool:
    return _as_utc(value) <= _now()


def _is_future(value: datetime) -> bool:
    return _as_utc(value) > _now()


def _auto_no_show(booking: Booking):
    """
    Lazy NO_SHOW evaluation.
    """
    if (
        booking.status == BookingStatus.CONFIRMED
        and _as_utc(booking.end_at) < _now()
    ):
        booking.status = BookingStatus.NO_SHOW


def _booking_expired_customer_message(booking: Booking) -> str:
    service = booking.service_name_snapshot or "your service"
    return (
        f"Your booking request for {service} expired because it was not "
        "approved before the appointment time. Kindly choose another time and re-book."
    )


def _booking_expired_salon_message(booking: Booking) -> str:
    customer_name = booking.customer.name if booking.customer else "The customer"
    service = booking.service_name_snapshot or "a service"
    return (
        f"{customer_name}'s booking request for {service} expired because it "
        "was not approved before the appointment time. Let them know your availability "
        "or invite them to re-book."
    )


def _auto_expire_pending(booking: Booking, *, db=None, notify: bool = True) -> bool:
    """
    Lazy EXPIRED evaluation for pending requests whose start time has passed.
    Returns True when the booking changed state.
    """
    if not (
        booking.status == BookingStatus.PENDING
        and _as_utc(booking.start_at) <= _now()
    ):
        return False

    booking.status = BookingStatus.EXPIRED
    booking.cancelled_by = None
    booking.cancel_reason = "Salon did not approve before the appointment time"

    if notify and db is not None:
        from service.chat import create_booking_expired_chat_event
        from service.notification.notification import create_notification

        salon_user_id = booking.salon.user_id if booking.salon else None
        customer_message = _booking_expired_customer_message(booking)
        salon_message = _booking_expired_salon_message(booking)

        if salon_user_id:
            create_notification(
                db=db,
                recipient_id=booking.customer_id,
                actor_id=salon_user_id,
                type="booking_expired",
                booking_id=booking.id,
                message=customer_message,
                commit=False,
            )
            create_notification(
                db=db,
                recipient_id=salon_user_id,
                actor_id=booking.customer_id,
                type="booking_expired",
                booking_id=booking.id,
                message=salon_message,
                commit=False,
            )

        create_booking_expired_chat_event(
            db=db,
            booking=booking,
            message=customer_message,
            commit=False,
        )

    return True
