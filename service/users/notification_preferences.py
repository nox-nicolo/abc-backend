from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.profile.notification_preferences import UserNotificationPreference
from pydantic_schemas.profile.notification_preferences import (
    ALLOWED_LEAD_MINUTES,
    NotificationPreferenceUpdate,
)


def _get_or_create(db: Session, user_id: str) -> UserNotificationPreference:
    pref = (
        db.query(UserNotificationPreference)
        .filter(UserNotificationPreference.user_id == user_id)
        .first()
    )
    if pref is None:
        pref = UserNotificationPreference(user_id=user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def get_preferences(db: Session, user_id: str) -> UserNotificationPreference:
    return _get_or_create(db, user_id)


def update_preferences(
    db: Session,
    user_id: str,
    payload: NotificationPreferenceUpdate,
) -> UserNotificationPreference:
    pref = _get_or_create(db, user_id)

    if payload.reminder_lead_minutes is not None:
        if payload.reminder_lead_minutes not in ALLOWED_LEAD_MINUTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"reminder_lead_minutes must be one of "
                    f"{sorted(ALLOWED_LEAD_MINUTES)}"
                ),
            )
        pref.reminder_lead_minutes = payload.reminder_lead_minutes

    for field in (
        "allow_likes",
        "allow_comments",
        "allow_bookings",
        "allow_promotions",
        "allow_reminders",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(pref, field, value)

    db.commit()
    db.refresh(pref)
    return pref
