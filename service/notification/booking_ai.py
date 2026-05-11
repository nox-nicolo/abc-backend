import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


TZ_TANZANIA = ZoneInfo("Africa/Dar_es_Salaam")
SEND_START_HOUR = 9
SEND_END_HOUR = 19
MAX_REMINDERS_PER_CYCLE = 3
BOOKING_LINK_BASE = os.getenv("BOOKING_LINK_BASE", "africanbeauty://booking")


@dataclass(frozen=True)
class BookingNotificationContext:
    customer_name: str
    service_type: str
    salon_name: str
    booking_date: str
    booking_time: str
    booking_link: str
    stylist_name: Optional[str] = None
    salon_address: Optional[str] = None
    weeks_since_last_visit: Optional[int] = None
    upcoming_event: Optional[str] = None
    reminder_number: int = 1


@dataclass(frozen=True)
class EventBookingNotificationContext:
    customer_name: str
    upcoming_event: str
    days_until_event: int
    salon_name: str
    service_type: str
    booking_link: str
    stylist_name: Optional[str] = None


@dataclass(frozen=True)
class PromotionNotificationContext:
    customer_name: str
    salon_name: str
    offer_title: str
    service_type: str
    booking_link: str
    discount_code: Optional[str] = None
    expires_at: Optional[str] = None
    stylist_name: Optional[str] = None


def is_allowed_send_time(now: Optional[datetime] = None) -> bool:
    local_now = (now or datetime.now(TZ_TANZANIA)).astimezone(TZ_TANZANIA)
    return SEND_START_HOUR <= local_now.hour < SEND_END_HOUR


def booking_link(booking_id: str) -> str:
    return f"{BOOKING_LINK_BASE}/{booking_id}"


def rebooking_link(booking_id: str) -> str:
    return f"{BOOKING_LINK_BASE}/rebook/{booking_id}"


def first_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean:
        return "there"
    return clean.split()[0]


def generate_booking_message(ctx: BookingNotificationContext) -> str:
    name = first_name(ctx.customer_name)
    service = _plain(ctx.service_type, fallback="your booking")
    salon = _plain(ctx.salon_name, fallback="the salon")
    stylist = _plain(ctx.stylist_name)
    event = _plain(ctx.upcoming_event)

    stylist_part = f" with {stylist}" if stylist else ""
    event_part = f" before {event}" if event else ""

    variants = [
        f"Hi {name}, your {service}{stylist_part} at {salon} is {ctx.booking_date} at {ctx.booking_time}. See you soon{event_part} 💛 {ctx.booking_link}",
        f"{name}, quick reminder: {service}{stylist_part} at {salon}, {ctx.booking_date} {ctx.booking_time}. Tap to check details ✨ {ctx.booking_link}",
        f"Hi {name}, {salon} is ready for your {service}{stylist_part} on {ctx.booking_date} at {ctx.booking_time} 🌸 {ctx.booking_link}",
    ]

    message = variants[min(max(ctx.reminder_number, 1), len(variants)) - 1]
    return _under_word_limit(message, ctx.booking_link)


def generate_booking_confirmation_message(
    ctx: BookingNotificationContext,
    *,
    reminder_lead_minutes: int,
) -> dict:
    name = first_name(ctx.customer_name)
    service = _plain(ctx.service_type, fallback="your booking")
    salon = _plain(ctx.salon_name, fallback="the salon")
    stylist = _plain(ctx.stylist_name)
    stylist_part = f" with Stylist {stylist}" if stylist else ""

    message = (
        f"Booking confirmed! ✅ Hi {name}, your {service} appointment at {salon} is booked "
        f"for {ctx.booking_date} at {ctx.booking_time}{stylist_part}. "
        f"We will remind you {reminder_lead_minutes} minutes before. See you then! "
        f"{ctx.booking_link}"
    )

    return {
        "channel": "in app notification",
        "message": _under_word_limit(message, ctx.booking_link, limit=60),
        "send_at": "immediately",
    }


def generate_rebooking_reminder_message(ctx: BookingNotificationContext) -> dict:
    name = first_name(ctx.customer_name)
    service = _plain(ctx.service_type, fallback="your beauty service")
    salon = _plain(ctx.salon_name, fallback="the salon")
    stylist = _plain(ctx.stylist_name)
    weeks = ctx.weeks_since_last_visit or 0

    stylist_part = f" with Stylist {stylist}" if stylist else ""
    when_part = f"It has been about {weeks} weeks" if weeks > 0 else "It may be time"
    message = (
        f"Hi {name} 🌸 {when_part} since your {service} at {salon}. "
        f"Book again{stylist_part} before the best slots fill up! {ctx.booking_link}"
    )

    return {
        "channel": "in app notification",
        "message": _under_word_limit(message, ctx.booking_link, limit=50),
        "send_at": "based on service rebooking cycle",
        "trigger": "rebooking_reminder",
    }


def generate_event_based_booking_message(
    ctx: EventBookingNotificationContext,
) -> dict:
    name = first_name(ctx.customer_name)
    event = _plain(ctx.upcoming_event, fallback="your event")
    service = _plain(ctx.service_type, fallback="your beauty appointment")
    salon = _plain(ctx.salon_name, fallback="your salon")
    stylist = _plain(ctx.stylist_name)

    timing = _event_timing(ctx.days_until_event)
    stylist_part = f" with Stylist {stylist}" if stylist else ""
    message = (
        f"Hi {name} 🎉 {event} is {timing}! Slots at {salon} are filling fast. "
        f"Book your {service}{stylist_part} before they are gone! {ctx.booking_link}"
    )

    return {
        "channel": "in app notification",
        "message": _under_word_limit(message, ctx.booking_link, limit=50),
        "send_at": "21 days before event",
        "trigger": "event_based",
    }


def generate_promotion_message(ctx: PromotionNotificationContext) -> dict:
    name = first_name(ctx.customer_name)
    salon = _plain(ctx.salon_name, fallback="your salon")
    offer = _plain(ctx.offer_title, fallback="a new offer")
    service = _plain(ctx.service_type, fallback="beauty service")
    stylist = _plain(ctx.stylist_name)
    code = _plain(ctx.discount_code)
    expires = _plain(ctx.expires_at)

    stylist_part = f" with Stylist {stylist}" if stylist else ""
    code_part = f" Use code {code}." if code else ""
    expires_part = f" Valid until {expires}." if expires else ""
    message = (
        f"Hi {name} 💛 {salon} has {offer} for {service}{stylist_part}."
        f"{code_part}{expires_part} Book direct with the salon: {ctx.booking_link}"
    )

    return {
        "channel": "in app notification",
        "message": _under_word_limit(message, ctx.booking_link, limit=50),
        "send_at": "immediately",
        "trigger": "promotion_campaign",
    }


def _plain(value: Optional[str], fallback: str = "") -> str:
    value = (value or "").strip()
    return value or fallback


def _event_timing(days_until_event: int) -> str:
    if days_until_event <= 1:
        return "tomorrow"
    if days_until_event == 7:
        return "in 1 week"
    if days_until_event % 7 == 0 and days_until_event <= 21:
        return f"in {days_until_event // 7} weeks"
    return f"in {days_until_event} days"


def rebooking_cycle_weeks(service_type: Optional[str]) -> int:
    service = (service_type or "").lower()
    if any(term in service for term in ("nail", "manicure", "pedicure")):
        return 3
    if any(term in service for term in ("braid", "cornrow", "twist", "loc")):
        return 5
    if any(term in service for term in ("facial", "skin", "wax")):
        return 4
    if any(term in service for term in ("treatment", "relax", "wash", "blow")):
        return 4
    if any(term in service for term in ("weave", "wig", "install")):
        return 4
    return 5


def _under_word_limit(message: str, link: str, *, limit: int = 50) -> str:
    words = message.split()
    if len(words) <= limit:
        return message

    compact = f"Hi {words[1].rstrip(',')}, booking reminder: check your appointment details 💛 {link}"
    return compact
