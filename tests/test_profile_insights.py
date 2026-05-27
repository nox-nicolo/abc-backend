from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.enumeration import BookingStatus, ServiceCreatedStatus
from models.auth.user import User
from models.booking.booking import Booking
from models.profile.insights import SalonInsightEvent
from models.profile.salon import Salon, SalonFollower, SalonServicePrice
from models.saved import SavedService
from models.services.service import Services, SubServices
from service.auth.permissions import UserPrincipal
from service.profile.insights import get_profile_insights, record_salon_service_tap
from tests.conftest import make_user


@pytest.fixture()
def insights_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            Salon.__table__,
            Services.__table__,
            SubServices.__table__,
            SalonServicePrice.__table__,
            SavedService.__table__,
            SalonFollower.__table__,
            Booking.__table__,
            SalonInsightEvent.__table__,
        ]
    )


def _principal(user, role):
    return UserPrincipal(user_id=user.id, role=role, user=user)


def test_customer_profile_insights_use_saved_followed_and_booking_data(insights_db):
    user = make_user(user_id="customer-1", role="customer")
    owner = make_user(user_id="owner-1", role="service")
    salon = Salon(id="salon-1", user_id=owner.id, title="Salon")
    service = Services(id="service-1", name="Hair", service_picture="hair.png")
    sub_service = SubServices(id="sub-1", service_id=service.id, name="Braids")
    offering = SalonServicePrice(
        id="offering-1",
        salon_id=salon.id,
        service_id=service.id,
        sub_service_id=sub_service.id,
        status=ServiceCreatedStatus.ACTIVE,
    )
    insights_db.add_all(
        [
            user,
            owner,
            salon,
            service,
            sub_service,
            offering,
            SavedService(user_id=user.id, salon_service_price_id=offering.id),
            SalonFollower(user_id=user.id, salon_id=salon.id),
            Booking(
                id="booking-1",
                customer_id=user.id,
                salon_id=salon.id,
                salon_service_price_id=offering.id,
                start_at=datetime.now(timezone.utc),
                end_at=datetime.now(timezone.utc) + timedelta(hours=1),
                status=BookingStatus.COMPLETED,
                service_name_snapshot="Braids",
                price_snapshot=Decimal("10000"),
                currency_snapshot="TZS",
                duration_minutes_snapshot=60,
            ),
        ]
    )
    insights_db.commit()

    result = get_profile_insights(db=insights_db, principal=_principal(user, "customer"))

    assert result["role"] == "customer"
    assert result["customer"]["saved_styles_count"] == 1
    assert result["customer"]["followed_salons_count"] == 1
    assert result["customer"]["recent_booking_categories"] == [{"name": "Braids", "count": 1}]


def test_salon_profile_insights_use_events_bookings_and_followers(insights_db):
    owner = make_user(user_id="owner-1", role="service")
    customer = make_user(user_id="customer-1", role="customer")
    salon = Salon(id="salon-1", user_id=owner.id, title="Salon")
    service = Services(id="service-1", name="Hair", service_picture="hair.png")
    sub_service = SubServices(id="sub-1", service_id=service.id, name="Braids")
    offering = SalonServicePrice(
        id="offering-1",
        salon_id=salon.id,
        service_id=service.id,
        sub_service_id=sub_service.id,
        status=ServiceCreatedStatus.ACTIVE,
    )
    now = datetime.now(timezone.utc)
    insights_db.add_all(
        [
            owner,
            customer,
            salon,
            service,
            sub_service,
            offering,
            SalonFollower(user_id=customer.id, salon_id=salon.id, created_at=now),
            SalonInsightEvent(salon_id=salon.id, user_id=customer.id, event_type="profile_view"),
            Booking(
                id="booking-1",
                customer_id=customer.id,
                salon_id=salon.id,
                salon_service_price_id=offering.id,
                start_at=now,
                end_at=now + timedelta(hours=1),
                status=BookingStatus.COMPLETED,
                service_name_snapshot="Braids",
                price_snapshot=Decimal("10000"),
                currency_snapshot="TZS",
                duration_minutes_snapshot=60,
            ),
            Booking(
                id="booking-2",
                customer_id=customer.id,
                salon_id=salon.id,
                salon_service_price_id=offering.id,
                start_at=now + timedelta(days=1),
                end_at=now + timedelta(days=1, hours=1),
                status=BookingStatus.COMPLETED,
                service_name_snapshot="Braids",
                price_snapshot=Decimal("10000"),
                currency_snapshot="TZS",
                duration_minutes_snapshot=60,
            ),
        ]
    )
    insights_db.commit()

    record_salon_service_tap(
        db=insights_db,
        salon_id=salon.id,
        salon_service_price_id=offering.id,
        user_id=customer.id,
    )

    result = get_profile_insights(db=insights_db, principal=_principal(owner, "salon_owner"))

    assert result["role"] == "salon"
    assert result["salon"]["profile_views"] == 1
    assert result["salon"]["service_taps"] == 1
    assert result["salon"]["returning_customers"] == 1
    assert result["salon"]["follower_growth"]["last_30_days"] == 1
