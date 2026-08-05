"""Provides the Test Booking test module for the backend application."""

import asyncio
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException, status

from core.enumeration import BookingStatus, ServiceCreatedStatus
from models.account.settings import UserAccountSettings
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.booking.booking import Booking, BookingEvent, ServiceReview
from models.profile.notification_preferences import UserNotificationPreference
from models.profile.salon import (
    Salon,
    SalonAvailabilityOverride,
    SalonLocation,
    SalonServicePrice,
    SalonStylist,
    SalonWorkingHour,
    StylistService,
)
from models.services.service import Services, SubServices
from pydantic_schemas.booking.booking import (
    BookingCancel,
    BookingCreate,
    BookingListPage,
    BookingReviewCreate,
    BookingReschedule,
)
from service.booking.booking import (
    assign_booking_stylist_service,
    cancel_booking_service,
    complete_booking_service,
    create_review_service,
    confirm_booking_service,
    get_booking_events_service,
    create_booking_service,
    get_availability_slots_service,
    get_booking_service,
    get_booking_stylists_for_offer,
    get_salons_for_style,
    get_salon_bookings_service,
    get_user_bookings_service,
    mark_no_show_bookings_for_scope,
    mark_no_show_service,
    reject_booking_service,
    reschedule_booking_service,
)
from service.booking.ratings import (
    salon_rating_summary,
    service_rating_summary,
    stylist_rating_summary,
    sub_service_rating_summary,
)

from tests.conftest import make_user


@pytest.fixture()
def booking_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            ProfilePicture.__table__,
            UserAccountSettings.__table__,
            Salon.__table__,
            SalonAvailabilityOverride.__table__,
            SalonLocation.__table__,
            SalonWorkingHour.__table__,
            SalonStylist.__table__,
            StylistService.__table__,
            Services.__table__,
            SubServices.__table__,
            SalonServicePrice.__table__,
            UserNotificationPreference.__table__,
            Booking.__table__,
            BookingEvent.__table__,
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


def test_customer_booking_list_includes_app_expected_fields(booking_db):
    booking, customer, _, _ = _seed_booking(booking_db)

    result = asyncio.run(
        get_user_bookings_service(
            db=booking_db,
            user_id=customer.id,
            status=None,
            upcoming=None,
            limit=20,
            offset=0,
        )
    )
    page = BookingListPage.model_validate(result)
    item = page.items[0]

    assert item.id == booking.id
    assert item.customer_id == customer.id
    assert item.customer_name == customer.name
    assert item.duration_minutes_snapshot == 90
    assert item.note == "Test booking"


def test_salon_booking_list_includes_app_expected_fields(booking_db):
    booking, customer, owner, _ = _seed_booking(booking_db)

    result = asyncio.run(
        get_salon_bookings_service(
            db=booking_db,
            user_id=owner.id,
            status=None,
            upcoming=None,
            date=None,
            limit=20,
            offset=0,
        )
    )
    page = BookingListPage.model_validate(result)
    item = page.items[0]

    assert item.id == booking.id
    assert item.customer_id == customer.id
    assert item.customer_name == customer.name
    assert item.duration_minutes_snapshot == 90
    assert item.note == "Test booking"


def test_salon_discovery_only_returns_bookable_offerings(booking_db):
    booking, customer, _, _ = _seed_booking(booking_db)
    valid_offering = booking.salon_service_price
    booking_db.add(
        SalonLocation(
            salon_id=booking.salon_id,
            street="Main",
            city="Dar es Salaam",
            country="TZ",
        )
    )
    invalid_offerings = [
        SalonServicePrice(
            id="inactive-offering",
            salon_id=valid_offering.salon_id,
            service_id=valid_offering.service_id,
            sub_service_id=valid_offering.sub_service_id,
            price_min=10000,
            price_max=12000,
            currency="TZS",
            duration_minutes=60,
            concurrent_capacity=1,
            status=ServiceCreatedStatus.INACTIVE,
        ),
        SalonServicePrice(
            id="missing-price-offering",
            salon_id=valid_offering.salon_id,
            service_id=valid_offering.service_id,
            sub_service_id=valid_offering.sub_service_id,
            price_min=None,
            price_max=12000,
            currency="TZS",
            duration_minutes=60,
            concurrent_capacity=1,
            status=ServiceCreatedStatus.ACTIVE,
        ),
        SalonServicePrice(
            id="zero-duration-offering",
            salon_id=valid_offering.salon_id,
            service_id=valid_offering.service_id,
            sub_service_id=valid_offering.sub_service_id,
            price_min=10000,
            price_max=12000,
            currency="TZS",
            duration_minutes=0,
            concurrent_capacity=1,
            status=ServiceCreatedStatus.ACTIVE,
        ),
        SalonServicePrice(
            id="zero-capacity-offering",
            salon_id=valid_offering.salon_id,
            service_id=valid_offering.service_id,
            sub_service_id=valid_offering.sub_service_id,
            price_min=10000,
            price_max=12000,
            currency="TZS",
            duration_minutes=60,
            concurrent_capacity=0,
            status=ServiceCreatedStatus.ACTIVE,
        ),
    ]
    booking_db.add_all(invalid_offerings)
    booking_db.commit()

    result = asyncio.run(
        get_salons_for_style(
            db=booking_db,
            sub_service_id=valid_offering.sub_service_id,
            limit=20,
            offset=0,
            current_user_id=customer.id,
        )
    )

    assert [offer.salon_service_price_id for offer in result["results"]] == [
        valid_offering.id
    ]
    assert result["results"][0].price == valid_offering.price_min


def test_booking_stylists_only_returns_active_assigned_stylists(booking_db):
    booking, _, _, _ = _seed_booking(booking_db)
    offering = booking.salon_service_price
    active_user = make_user(user_id="active-stylist-user", role="service")
    inactive_user = make_user(user_id="inactive-stylist-user", role="service")
    unassigned_user = make_user(user_id="unassigned-stylist-user", role="service")
    active_stylist = SalonStylist(
        id="active-stylist",
        salon_id=booking.salon_id,
        user_id=active_user.id,
        title="Braider",
        is_active=True,
    )
    inactive_stylist = SalonStylist(
        id="inactive-stylist",
        salon_id=booking.salon_id,
        user_id=inactive_user.id,
        is_active=False,
    )
    unassigned_stylist = SalonStylist(
        id="unassigned-stylist",
        salon_id=booking.salon_id,
        user_id=unassigned_user.id,
        is_active=True,
    )
    booking_db.add_all(
        [
            active_user,
            inactive_user,
            unassigned_user,
            active_stylist,
            inactive_stylist,
            unassigned_stylist,
            StylistService(
                stylist_id=active_stylist.id,
                salon_service_price_id=offering.id,
            ),
            StylistService(
                stylist_id=inactive_stylist.id,
                salon_service_price_id=offering.id,
            ),
        ]
    )
    booking_db.commit()

    result = asyncio.run(
        get_booking_stylists_for_offer(
            db=booking_db,
            salon_service_price_id=offering.id,
            limit=20,
            offset=0,
        )
    )

    assert [stylist.stylist_id for stylist in result["results"]] == [
        active_stylist.id
    ]
    assert result["results"][0].rating == 0.0
    assert result["results"][0].reviews_count == 0


def test_create_booking_rejects_busy_selected_stylist(booking_db, monkeypatch):
    booking, customer, _, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    offering = booking.salon_service_price
    offering.concurrent_capacity = 2
    stylist_user = make_user(user_id="busy-stylist-user", role="service")
    stylist = SalonStylist(
        id="busy-stylist",
        salon_id=booking.salon_id,
        user_id=stylist_user.id,
        is_active=True,
    )
    booking.stylist_id = stylist.id
    target_day = booking.start_at.astimezone(timezone(timedelta(hours=3))).date()
    booking_db.add_all(
        [
            stylist_user,
            stylist,
            StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=offering.id,
            ),
            SalonWorkingHour(
                salon_id=booking.salon_id,
                day_of_week=target_day.weekday(),
                is_open=True,
                open_time=time(0, 0),
                close_time=time(23, 59),
            ),
        ]
    )
    booking_db.commit()
    _silence_booking_side_effects(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            create_booking_service(
                db=booking_db,
                payload=BookingCreate(
                    salon_service_price_id=offering.id,
                    stylist_id=stylist.id,
                    start_at=booking.start_at,
                ),
                user_id=customer.id,
            )
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert "stylist" in exc.value.detail.lower()


def test_salon_can_assign_available_stylist_to_booking(booking_db):
    booking, _, owner, _ = _seed_booking(booking_db)
    stylist_user = make_user(user_id="assign-stylist-user", role="service")
    stylist = SalonStylist(
        id="assign-stylist",
        salon_id=booking.salon_id,
        user_id=stylist_user.id,
        is_active=True,
    )
    booking_db.add_all(
        [
            stylist_user,
            stylist,
            StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=booking.salon_service_price_id,
            ),
        ]
    )
    booking_db.commit()

    result = asyncio.run(
        assign_booking_stylist_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
            stylist_id=stylist.id,
        )
    )

    assert result.stylist_id == stylist.id


def test_salon_assign_stylist_rejects_busy_stylist(booking_db):
    booking, customer, owner, _ = _seed_booking(booking_db)
    offering = booking.salon_service_price
    offering.concurrent_capacity = 2
    stylist_user = make_user(user_id="assign-busy-stylist-user", role="service")
    stylist = SalonStylist(
        id="assign-busy-stylist",
        salon_id=booking.salon_id,
        user_id=stylist_user.id,
        is_active=True,
    )
    booking_db.add_all(
        [
            stylist_user,
            stylist,
            StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=offering.id,
            ),
            Booking(
                id="assign-conflicting-booking",
                customer_id=customer.id,
                salon_id=booking.salon_id,
                salon_service_price_id=offering.id,
                stylist_id=stylist.id,
                start_at=booking.start_at,
                end_at=booking.end_at,
                status=BookingStatus.CONFIRMED,
                service_name_snapshot=booking.service_name_snapshot,
                price_snapshot=booking.price_snapshot,
                currency_snapshot=booking.currency_snapshot,
                duration_minutes_snapshot=booking.duration_minutes_snapshot,
            ),
        ]
    )
    booking_db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            assign_booking_stylist_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=owner.id,
                stylist_id=stylist.id,
            )
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert "stylist" in exc.value.detail.lower()


def test_availability_hides_busy_selected_stylist_slot(booking_db):
    booking, _, _, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    offering = booking.salon_service_price
    offering.concurrent_capacity = 2
    stylist_user = make_user(user_id="availability-stylist-user", role="service")
    stylist = SalonStylist(
        id="availability-stylist",
        salon_id=booking.salon_id,
        user_id=stylist_user.id,
        is_active=True,
    )
    booking.stylist_id = stylist.id
    local_start = booking.start_at.astimezone(timezone(timedelta(hours=3)))
    booking_db.add_all(
        [
            stylist_user,
            stylist,
            StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=offering.id,
            ),
            SalonWorkingHour(
                salon_id=booking.salon_id,
                day_of_week=local_start.date().weekday(),
                is_open=True,
                open_time=time(local_start.hour, local_start.minute),
                close_time=(local_start + timedelta(hours=3)).time(),
            ),
        ]
    )
    booking_db.commit()

    result = asyncio.run(
        get_availability_slots_service(
            db=booking_db,
            salon_service_price_id=offering.id,
            stylist_id=stylist.id,
            start_date=local_start.date(),
            days=1,
        )
    )

    starts = {slot["start_at"] for slot in result["items"][0]["slots"]}
    assert booking.start_at not in starts


def test_reschedule_rejects_fully_booked_slot(booking_db, monkeypatch):
    booking, customer, _, _ = _seed_booking(booking_db)
    offering = booking.salon_service_price
    local_tz = timezone(timedelta(hours=3))
    target_day = (datetime.now(local_tz) + timedelta(days=3)).date()
    target_local = datetime.combine(target_day, time(10, 0), tzinfo=local_tz)
    target_start = target_local.astimezone(timezone.utc)
    target_end = target_start + timedelta(minutes=offering.duration_minutes)
    booking_db.add(
        SalonWorkingHour(
            salon_id=booking.salon_id,
            day_of_week=target_day.weekday(),
            is_open=True,
            open_time=time(8, 0),
            close_time=time(18, 0),
        )
    )
    booking_db.add(
        Booking(
            id="conflicting-booking",
            customer_id=customer.id,
            salon_id=booking.salon_id,
            salon_service_price_id=offering.id,
            start_at=target_start,
            end_at=target_end,
            status=BookingStatus.CONFIRMED,
            service_name_snapshot=booking.service_name_snapshot,
            price_snapshot=booking.price_snapshot,
            currency_snapshot=booking.currency_snapshot,
            duration_minutes_snapshot=booking.duration_minutes_snapshot,
        )
    )
    booking_db.commit()
    _silence_booking_side_effects(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            reschedule_booking_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=customer.id,
                payload=BookingReschedule(start_at=target_start),
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "This time slot is fully booked"


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


def test_complete_rejects_booking_before_end_time(booking_db, monkeypatch):
    booking, _, owner, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    booking.start_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    booking.end_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking_db.commit()
    _silence_booking_side_effects(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            complete_booking_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=owner.id,
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Booking has not ended yet"


def test_customer_review_feeds_salon_stylist_service_and_sub_service_ratings(booking_db):
    booking, customer, _, _ = _seed_booking(booking_db, status=BookingStatus.COMPLETED)
    stylist_user = make_user(user_id="stylist-user", role="service")
    stylist = SalonStylist(
        id="stylist-1",
        salon_id=booking.salon_id,
        user_id=stylist_user.id,
        title="Senior Stylist",
        is_active=True,
    )
    booking_db.add_all(
        [
            stylist_user,
            stylist,
            StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=booking.salon_service_price_id,
            ),
        ]
    )
    booking.stylist_id = stylist.id
    booking_db.commit()

    review = asyncio.run(
        create_review_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=customer.id,
            payload=BookingReviewCreate(rating=5, comment="Great service"),
        )
    )

    assert review.booking_id == booking.id
    assert review.user_id == customer.id
    assert review.rating == 5
    assert review.comment == "Great service"
    assert review.salon_id == booking.salon_id
    assert review.stylist_id == stylist.id
    assert review.salon_service_price_id == booking.salon_service_price_id
    assert review.service_id == booking.salon_service_price.service_id
    assert review.sub_service_id == booking.salon_service_price.sub_service_id

    assert salon_rating_summary(booking_db, salon_id=booking.salon_id) == {
        "average": 5.0,
        "count": 1,
    }
    assert stylist_rating_summary(booking_db, stylist_id=stylist.id) == {
        "average": 5.0,
        "count": 1,
    }
    assert service_rating_summary(
        booking_db,
        service_id=booking.salon_service_price.service_id,
    ) == {
        "average": 5.0,
        "count": 1,
    }
    assert sub_service_rating_summary(
        booking_db,
        sub_service_id=booking.salon_service_price.sub_service_id,
    ) == {
        "average": 5.0,
        "count": 1,
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            create_review_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=customer.id,
                payload=BookingReviewCreate(rating=4),
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "You already reviewed this booking"


def test_review_rejects_non_customer_or_incomplete_booking(booking_db):
    booking, customer, owner, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)

    with pytest.raises(HTTPException) as owner_exc:
        asyncio.run(
            create_review_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=owner.id,
                payload=BookingReviewCreate(rating=5),
            )
        )

    assert owner_exc.value.status_code == 403
    assert owner_exc.value.detail == "Not your booking"

    with pytest.raises(HTTPException) as incomplete_exc:
        asyncio.run(
            create_review_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=customer.id,
                payload=BookingReviewCreate(rating=5),
            )
        )

    assert incomplete_exc.value.status_code == 400
    assert incomplete_exc.value.detail == "You can only review a completed booking"


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


def test_background_maintenance_marks_ended_confirmed_bookings_no_show(booking_db):
    booking, _, _, _ = _seed_booking(booking_db, status=BookingStatus.CONFIRMED)
    booking.start_at = datetime.now(timezone.utc) - timedelta(hours=2)
    booking.end_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    booking_db.commit()

    marked = mark_no_show_bookings_for_scope(booking_db)
    booking_db.commit()
    booking_db.refresh(booking)

    assert marked == 1
    assert booking.status == BookingStatus.NO_SHOW


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


def test_booking_lifecycle_events_are_recorded(booking_db, monkeypatch):
    _silence_booking_side_effects(monkeypatch)
    booking, customer, owner, _ = _seed_booking(booking_db, status=BookingStatus.PENDING)
    stylist_user = make_user(user_id="event-stylist-user", role="service")
    stylist = SalonStylist(
        id="event-stylist",
        salon_id=booking.salon_id,
        user_id=stylist_user.id,
        title="Senior Stylist",
        is_active=True,
    )
    booking_db.add_all([stylist_user, stylist])
    booking_db.flush()
    reschedule_start = booking.start_at + timedelta(days=1)
    target_day = reschedule_start.astimezone(timezone(timedelta(hours=3))).date()
    booking_db.add_all(
        [
            StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=booking.salon_service_price_id,
            ),
            SalonWorkingHour(
                salon_id=booking.salon_id,
                day_of_week=target_day.weekday(),
                is_open=True,
                open_time=time(0, 0),
                close_time=time(23, 59),
            ),
        ]
    )
    booking_db.commit()

    asyncio.run(
        confirm_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )
    asyncio.run(
        assign_booking_stylist_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
            stylist_id=stylist.id,
        )
    )
    asyncio.run(
        reschedule_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=customer.id,
            payload=BookingReschedule(start_at=reschedule_start),
        )
    )

    booking.start_at = datetime.now(timezone.utc) - timedelta(hours=2)
    booking.end_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    booking.status = BookingStatus.CONFIRMED
    booking_db.commit()

    asyncio.run(
        complete_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )
    asyncio.run(
        create_review_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=customer.id,
            payload=BookingReviewCreate(rating=5, comment="Great"),
        )
    )

    events = asyncio.run(
        get_booking_events_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=customer.id,
        )
    )
    event_types = [event.event_type for event in events]

    assert event_types == [
        "confirmed",
        "stylist_assigned",
        "rescheduled",
        "completed",
        "reviewed",
    ]
    assert events[1].event_metadata["stylist_id"] == stylist.id
    assert events[2].event_metadata["previous_start_at"] is not None
    assert events[-1].event_metadata["rating"] == 5


def test_booking_events_are_not_visible_to_strangers(booking_db, monkeypatch):
    _silence_booking_side_effects(monkeypatch)
    booking, _, owner, stranger = _seed_booking(booking_db, status=BookingStatus.PENDING)
    asyncio.run(
        confirm_booking_service(
            db=booking_db,
            booking_id=booking.id,
            user_id=owner.id,
        )
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_booking_events_service(
                db=booking_db,
                booking_id=booking.id,
                user_id=stranger.id,
            )
        )

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
