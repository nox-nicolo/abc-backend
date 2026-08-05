"""Provides the Test Notifications test module for the backend application."""

import pytest
from datetime import datetime, timedelta, timezone

from models.auth.user import User
from models.auth.profile_picture import ProfilePicture
from models.notifications.notification import Notification
from models.profile.notification_preferences import UserNotificationPreference
from models.profile.salon import Salon
from models.mute import UserMute
from pydantic_schemas.profile.notification_preferences import NotificationPreferenceUpdate
from service.notification import notification as notification_service
from service.users.notification_preferences import update_preferences

from tests.conftest import make_user


@pytest.fixture()
def notification_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            ProfilePicture.__table__,
            Salon.__table__,
            UserNotificationPreference.__table__,
            UserMute.__table__,
            Notification.__table__,
        ]
    )


@pytest.fixture(autouse=True)
def disable_push(monkeypatch):
    calls = []

    def fake_send_push_to_user(**kwargs):
        calls.append(kwargs)
        return {"sent": True}

    monkeypatch.setattr(notification_service, "send_push_to_user", fake_send_push_to_user)
    return calls


def test_create_notification_skips_self_actions(notification_db, disable_push):
    user = make_user(user_id="user-1")
    notification_db.add(user)
    notification_db.commit()

    result = notification_service.create_notification(
        db=notification_db,
        recipient_id=user.id,
        actor_id=user.id,
        type="like",
    )

    assert result is None
    assert notification_db.query(Notification).count() == 0
    assert disable_push == []


def test_create_notification_respects_user_preferences(notification_db, disable_push):
    recipient = make_user(user_id="recipient")
    actor = make_user(user_id="actor")
    notification_db.add_all(
        [
            recipient,
            actor,
            UserNotificationPreference(
                user_id=recipient.id,
                allow_likes=False,
                allow_comments=True,
                allow_bookings=True,
                allow_promotions=True,
                allow_reminders=True,
            ),
        ]
    )
    notification_db.commit()

    result = notification_service.create_notification(
        db=notification_db,
        recipient_id=recipient.id,
        actor_id=actor.id,
        type="like",
    )

    assert result is None
    assert notification_db.query(Notification).count() == 0
    assert disable_push == []


def test_welcome_notification_is_idempotent(notification_db, disable_push):
    user = make_user(user_id="welcome-user")
    notification_db.add(user)
    notification_db.commit()

    first = notification_service.create_welcome_notification(
        db=notification_db,
        user_id=user.id,
    )
    second = notification_service.create_welcome_notification(
        db=notification_db,
        user_id=user.id,
    )

    assert first.id == second.id
    assert notification_db.query(Notification).count() == 1
    assert len(disable_push) == 1
    assert disable_push[0]["title"] == "Welcome to African Beauty"


def test_promotion_preferred_time_is_saved(notification_db):
    user = make_user(user_id="promotion-time-user")
    notification_db.add(user)
    notification_db.commit()

    pref = update_preferences(
        notification_db,
        user.id,
        NotificationPreferenceUpdate(promotions_preferred_time="18:30"),
    )

    assert pref.promotions_preferred_time == "18:30"


def test_scheduled_notification_waits_until_delivery_time(notification_db, disable_push):
    recipient = make_user(user_id="scheduled-recipient")
    actor = make_user(user_id="scheduled-actor")
    notification_db.add_all([recipient, actor])
    notification_db.commit()

    scheduled_for = datetime.now(timezone.utc) + timedelta(hours=2)
    notification = notification_service.create_notification(
        db=notification_db,
        recipient_id=recipient.id,
        actor_id=actor.id,
        type="salon_promotion_campaign",
        message="A later offer",
        scheduled_for=scheduled_for,
    )

    listed = notification_service.list_notifications(
        db=notification_db,
        user_id=recipient.id,
    )

    assert notification.delivery_status == "scheduled"
    assert notification.scheduled_for.replace(tzinfo=timezone.utc) == scheduled_for
    assert listed.items == []
    assert disable_push == []
