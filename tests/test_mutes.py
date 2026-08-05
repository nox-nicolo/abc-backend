"""Provides the Test Mutes test module for the backend application."""

from datetime import datetime, timedelta, timezone

import pytest

from models.auth.user import User
from models.mute import UserMute
from service.users.mutes import list_mutes, mute_target
from tests.conftest import make_user


@pytest.fixture()
def mute_db(db_session_factory):
    yield from db_session_factory([User.__table__, UserMute.__table__])


def test_list_mutes_filters_and_sorts(mute_db):
    user = make_user()
    mute_db.add(user)
    mute_db.add_all(
        [
            UserMute(
                user_id=user.id,
                target_type="salon",
                target_id="salon-1",
                reason="Too many promos",
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
            UserMute(
                user_id=user.id,
                target_type="user",
                target_id="user-1",
                reason="Spam comments",
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )
    mute_db.commit()

    filtered = list_mutes(db=mute_db, user_id=user.id, q="promo", sort="newest")
    assert [item.target_id for item in filtered["items"]] == ["salon-1"]

    sorted_by_type = list_mutes(db=mute_db, user_id=user.id, sort="type")
    assert [item.target_type for item in sorted_by_type["items"]] == ["salon", "user"]


def test_mute_target_saves_and_updates_reason(mute_db):
    user = make_user()
    target = make_user()
    mute_db.add_all([user, target])
    mute_db.commit()

    created = mute_target(
        db=mute_db,
        user_id=user.id,
        target_type="user",
        target_id=target.id,
        reason="Harassment",
    )
    assert created.reason == "Harassment"

    updated = mute_target(
        db=mute_db,
        user_id=user.id,
        target_type="user",
        target_id=target.id,
        reason="Repeated spam",
    )
    assert updated.id == created.id
    assert updated.reason == "Repeated spam"
