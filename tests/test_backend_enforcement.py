from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from models.account.settings import UserAccountSettings
from models.auth.user import User
from models.profile.salon import Salon
from pydantic_schemas.customer.profile import CustomerProfileResponse, CustomerStatsSchema
from service.account.enforcement import (
    apply_customer_profile_visibility,
    is_blocked_between,
    salon_booking_rules_for_salon,
)
from tests.conftest import make_user


@pytest.fixture()
def enforcement_db(db_session_factory):
    yield from db_session_factory([User.__table__, UserAccountSettings.__table__, Salon.__table__])


def test_customer_profile_visibility_hides_public_fields(enforcement_db):
    user = make_user(user_id="customer-1")
    viewer = make_user(user_id="viewer-1")
    enforcement_db.add_all(
        [
            user,
            viewer,
            UserAccountSettings(
                user_id=user.id,
                settings={
                    "customer_profile_preview_visibility": {
                        "photo": False,
                        "bio": False,
                        "city": False,
                        "following": False,
                        "saved": False,
                        "booking_activity": False,
                    }
                },
            ),
        ]
    )
    enforcement_db.commit()

    profile = CustomerProfileResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        profile_picture="https://example.test/avatar.jpg",
        bio="Hidden bio",
        city="Dar es Salaam",
        country="TZ",
        preferred_services=["Braids"],
        stats=CustomerStatsSchema(following_count=4, bookings_count=3, reviews_count=2),
    )

    visible = apply_customer_profile_visibility(
        db=enforcement_db,
        profile=profile,
        target_user_id=user.id,
        viewer_user_id=viewer.id,
    )

    assert visible.profile_picture is None
    assert visible.bio is None
    assert visible.city is None
    assert visible.preferred_services == []
    assert visible.stats.bookings_count == 0


def test_blocked_accounts_match_id_or_username(enforcement_db):
    blocker = make_user(user_id="blocker-1")
    blocked = make_user(user_id="blocked-1", username="blocked_user")
    enforcement_db.add_all(
        [
            blocker,
            blocked,
            UserAccountSettings(
                user_id=blocker.id,
                settings={"customer_blocked_accounts": ["blocked_user"]},
            ),
        ]
    )
    enforcement_db.commit()

    assert is_blocked_between(enforcement_db, blocker.id, blocked.id) is True


def test_only_me_customer_profile_is_not_public(enforcement_db):
    user = make_user(user_id="customer-2")
    viewer = make_user(user_id="viewer-2")
    enforcement_db.add_all(
        [
            user,
            viewer,
            UserAccountSettings(
                user_id=user.id,
                settings={
                    "customer_profile_preview_visibility": {
                        "audience": "Only me",
                    }
                },
            ),
        ]
    )
    enforcement_db.commit()

    profile = CustomerProfileResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        stats=CustomerStatsSchema(),
    )

    with pytest.raises(HTTPException) as exc:
        apply_customer_profile_visibility(
            db=enforcement_db,
            profile=profile,
            target_user_id=user.id,
            viewer_user_id=viewer.id,
        )

    assert exc.value.status_code == 404


def test_salon_booking_rules_are_read_from_owner_settings(enforcement_db):
    owner = make_user(user_id="owner-1", role="service")
    salon = Salon(id="salon-1", user_id=owner.id, title="Rules Salon", created_at=datetime.now(timezone.utc))
    enforcement_db.add_all(
        [
            owner,
            salon,
            UserAccountSettings(
                user_id=owner.id,
                settings={
                    "salon_booking_rules": {
                        "minimum_notice_hours": 24,
                        "cancel_window_hours": 48,
                        "slot_interval_minutes": 45,
                        "buffer_minutes": 20,
                        "auto_confirm": True,
                        "allow_customer_notes": False,
                    }
                },
            ),
        ]
    )
    enforcement_db.commit()

    rules = salon_booking_rules_for_salon(enforcement_db, salon.id)

    assert rules.minimum_notice_hours == 24
    assert rules.cancel_window_hours == 48
    assert rules.slot_interval_minutes == 45
    assert rules.buffer_minutes == 20
    assert rules.auto_confirm is True
    assert rules.allow_customer_notes is False
