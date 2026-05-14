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
