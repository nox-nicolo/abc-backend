# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

from datetime import datetime, timezone

from core.enumeration import BookingStatus
from models.booking.booking import Booking


def _now():
    return datetime.now(timezone.utc)


def _auto_no_show(booking: Booking):
    """
    Lazy NO_SHOW evaluation.
    """
    if (
        booking.status == BookingStatus.CONFIRMED
        and booking.end_at < _now()
    ):
        booking.status = BookingStatus.NO_SHOW
