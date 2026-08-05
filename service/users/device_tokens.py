"""Provides the Device Tokens business logic module for users workflows."""

from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from models.notifications.device_token import UserDeviceToken
from pydantic_schemas.users.device_token import (
    DeviceTokenListResponse,
    DeviceTokenResponse,
    DeviceTokenUpsert,
)

logger = logging.getLogger("abc.push.tokens")


def _to_response(row: UserDeviceToken) -> DeviceTokenResponse:
    return DeviceTokenResponse(
        id=row.id,
        device_id=row.device_id,
        platform=row.platform,
        push_provider=row.push_provider,
        is_active=row.is_active,
        last_seen_at=row.last_seen_at,
    )


def upsert_device_token(*, db: Session, user_id: str, payload: DeviceTokenUpsert) -> DeviceTokenResponse:
    now = datetime.now(timezone.utc)
    row = (
        db.query(UserDeviceToken)
        .filter(
            UserDeviceToken.user_id == user_id,
            UserDeviceToken.device_id == payload.device_id,
        )
        .first()
    )
    if row is None:
        row = UserDeviceToken(
            user_id=user_id,
            device_id=payload.device_id,
            platform=payload.platform,
            push_provider=payload.push_provider,
            push_token=payload.push_token,
            app_version=payload.app_version,
            build_number=payload.build_number,
            is_active=True,
            last_seen_at=now,
        )
        db.add(row)
    else:
        row.platform = payload.platform
        row.push_provider = payload.push_provider
        row.push_token = payload.push_token
        row.app_version = payload.app_version
        row.build_number = payload.build_number
        row.is_active = True
        row.last_seen_at = now

    db.commit()
    db.refresh(row)
    logger.info(
        "FCM device token registered for user %s device %s platform %s",
        user_id,
        row.device_id,
        row.platform,
    )
    return _to_response(row)


def list_device_tokens(*, db: Session, user_id: str) -> DeviceTokenListResponse:
    rows = (
        db.query(UserDeviceToken)
        .filter(UserDeviceToken.user_id == user_id)
        .order_by(UserDeviceToken.last_seen_at.desc())
        .all()
    )
    return DeviceTokenListResponse(items=[_to_response(row) for row in rows])


def deactivate_device_token(*, db: Session, user_id: str, device_id: str) -> dict:
    row = (
        db.query(UserDeviceToken)
        .filter(
            UserDeviceToken.user_id == user_id,
            UserDeviceToken.device_id == device_id,
        )
        .first()
    )
    if row is not None:
        row.is_active = False
        row.last_seen_at = datetime.now(timezone.utc)
        db.commit()
    return {"device_id": device_id, "is_active": False}
