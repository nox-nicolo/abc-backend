import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from core.enumeration import BookingStatus, ServiceCreatedStatus
from models.account.settings import UserAccountSettings
from models.auth.user import User
from models.booking.booking import Booking, ServiceReview
from models.profile.notification_preferences import UserNotificationPreference
from models.profile.salon import Salon, SalonServicePrice
from models.services.service import Services, SubServices
from pydantic_schemas.booking.booking import BookingCancel
from service.booking.booking import (
    cancel_booking_service,
    complete_booking_service,
    confirm_booking_service,
    get_booking_service,
    mark_no_show_service,
    reject_booking_service,
)

from tests.conftest import make_user


@pytest.fixture()
def booking_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            UserAccountSettings.__table__,
            Salon.__table__,
            Services.__table__,
            SubServices.__table__,
            SalonServicePrice.__table__,
            UserNotificationPreference.__table__,
            Booking.__table__,
            ServiceReview.__table__,
        ]
    )


def _seed_booking(booking_db, *, status=BookingStatus.PENDING):
    customer = make_user(user_id="customer", role="customer")
    owner = make_user(user_id="owner", role="service")
    stranger = make_user(user_id="stranger", role="customer")
    salon = Salon(id="salon-1", user_id=owner.id, title="Owner Salon")
    service = Services(id="service-1", name="Hair", service_picture="hair.png")
    sub_service = SubServices(
        id="sub-service-1",
        service_id=service.id,
        name="Braids",
        is_event=False,
    )
    offering = SalonServicePrice(
        id="offering-1",
        salon_id=salon.id,
        service_id=service.id,
        sub_service_id=sub_service.id,
        price_min=25000,
        price_max=30000,
        currency="TZS",
        duration_minutes=90,
        concurrent_capacity=1,
        status=ServiceCreatedStatus.ACTIVE,
    )
    booking = Booking(
        id="booking-1",
        customer_id=customer.id,
        salon_id=salon.id,
        salon_service_price_id=offering.id,
        start_at=datetime.now(timezone.utc) + timedelta(days=2),
        end_at=datetime.now(timezone.utc) + timedelta(days=2, minutes=90),
        status=status,
        service_name_snapshot=sub_service.name,
        price_snapshot=Decimal("25000"),
        currency_snapshot="TZS",
        duration_minutes_snapshot=90,
        note="Test booking",
    )
    booking_db.add_all(
        [customer, owner, stranger, salon, service, sub_service, offering, booking]
    )
    booking_db.commit()
    return booking, customer, owner, stranger


def _silence_booking_side_effects(monkeypatch):
    monkeypatch.setattr("service.booking.booking.create_notification", lambda **_: None)
    monkeypatch.setattr("service.booking.booking.create_booking_chat_event", lambda **_: None)
    monkeypatch.setattr(
        "service.booking.booking.create_booking_confirmed_chat_event",
        lambda **_: None,
    )


def test_get_booking_allows_customer_and_salon_owner(booking_db):
    booking, customer, owner, _ = _seed_booking(booking_db)

    customer_result = asyncio.run(
        get_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=customer.id,
        )
    )
    owner_result = asyncio.run(
        get_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )

    assert customer_result.id == booking.id
    assert owner_result.id == booking.id


def test_get_booking_rejects_unrelated_user(booking_db):
    booking, _, _, stranger = _seed_booking(booking_db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_booking_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=stranger.id,
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Access denied"


def test_customer_can_cancel_pending_booking(booking_db, monkeypatch):
    booking, customer, _, _ = _seed_booking(booking_db)
    _silence_booking_side_effects(monkeypatch)

    result = asyncio.run(
        cancel_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=customer.id,
            payload=BookingCancel(reason="Plans changed"),
        )
    )

    assert result.status == BookingStatus.CANCELLED
    assert result.cancelled_by == "user"
    assert result.cancel_reason == "Plans changed"


def test_salon_can_confirm_pending_booking(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db)
    _silence_booking_side_effects(monkeypatch)

    result = asyncio.run(
        confirm_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )

    assert result.status == BookingStatus.CONFIRMED


def test_confirm_rejects_non_pending_booking(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db, status=BookingStatus.CANCELLED)
    _silence_booking_side_effects(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            confirm_booking_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=owner.id,
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Booking cannot be confirmed"


def test_salon_can_reject_pending_booking(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db)
    _silence_booking_side_effects(monkeypatch)

    result = asyncio.run(
        reject_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )

    assert result.status == BookingStatus.REJECTED


def test_salon_can_complete_started_confirmed_booking(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    booking.start_at = datetime.now(timezone.utc) - timedelta(hours=2)
    booking.end_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    booking_db.commit()
    _silence_booking_side_effects(monkeypatch)

    result = asyncio.run(
        complete_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )

    assert result.status == BookingStatus.COMPLETED


def test_salon_can_mark_ended_confirmed_booking_no_show(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    booking.start_at = datetime.now(timezone.utc) - timedelta(hours=2)
    booking.end_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    booking_db.commit()
    _silence_booking_side_effects(monkeypatch)

    result = asyncio.run(
        mark_no_show_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )

    assert result.status == BookingStatus.NO_SHOW


def test_no_show_rejects_booking_before_end_time(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    _silence_booking_side_effects(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            mark_no_show_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=owner.id,
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Booking has not ended yet"
