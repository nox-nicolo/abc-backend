import logging
import os
import json
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from models.notifications.device_token import UserDeviceToken

logger = logging.getLogger("abc.push")


def _credential_source() -> Optional[str]:
    if os.getenv("FIREBASE_ADMIN_CREDENTIALS_JSON"):
        return "FIREBASE_ADMIN_CREDENTIALS_JSON"
    if os.getenv("FIREBASE_ADMIN_CREDENTIALS"):
        return "FIREBASE_ADMIN_CREDENTIALS"
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return "GOOGLE_APPLICATION_CREDENTIALS"
    return None


@lru_cache(maxsize=1)
def _firebase_app():
    credentials_path = os.getenv("FIREBASE_ADMIN_CREDENTIALS") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_json = os.getenv("FIREBASE_ADMIN_CREDENTIALS_JSON")
    if not credentials_path and not credentials_json:
        logger.warning(
            "FCM disabled: set FIREBASE_ADMIN_CREDENTIALS, "
            "FIREBASE_ADMIN_CREDENTIALS_JSON, or GOOGLE_APPLICATION_CREDENTIALS"
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception:
        logger.warning("FCM disabled: firebase-admin is not installed")
        return None

    try:
        if firebase_admin._apps:
            return firebase_admin.get_app()
        if credentials_json:
            cred = credentials.Certificate(json.loads(credentials_json))
        else:
            cred = credentials.Certificate(credentials_path)
        return firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("FCM initialization failed")
        return None


def push_service_status(*, db: Session, user_id: str) -> dict:
    active_tokens = (
        db.query(UserDeviceToken)
        .filter(
            UserDeviceToken.user_id == user_id,
            UserDeviceToken.is_active.is_(True),
            UserDeviceToken.push_provider == "fcm",
        )
        .count()
    )
    configured = _credential_source() is not None
    return {
        "configured": configured,
        "credential_source": _credential_source(),
        "firebase_ready": _firebase_app() is not None if configured else False,
        "active_fcm_tokens": active_tokens,
    }


def send_push_to_user(
    *,
    db: Session,
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict[str, str]] = None,
    commit_changes: bool = True,
) -> int:
    app = _firebase_app()
    if app is None:
        logger.warning("FCM send skipped for user %s: Firebase Admin is not ready", user_id)
        return 0

    try:
        from firebase_admin import messaging
    except Exception:
        logger.warning("FCM send skipped: firebase-admin messaging unavailable")
        return 0

    rows = (
        db.query(UserDeviceToken)
        .filter(
            UserDeviceToken.user_id == user_id,
            UserDeviceToken.is_active.is_(True),
            UserDeviceToken.push_provider == "fcm",
        )
        .all()
    )
    if not rows:
        logger.warning("FCM send skipped for user %s: no active FCM device tokens", user_id)
        return 0

    sent = 0
    push_data = {str(k): "" if v is None else str(v) for k, v in (data or {}).items()}
    push_data.setdefault("title", title)
    push_data.setdefault("body", body)

    for row in rows:
        message = messaging.Message(
            token=row.push_token,
            notification=messaging.Notification(title=title, body=body),
            data=push_data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="abc_high_importance",
                    sound="default",
                    priority="high",
                    default_sound=True,
                    default_vibrate_timings=True,
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1),
                ),
            ),
        )
        try:
            messaging.send(message, app=app)
            sent += 1
            logger.info("FCM sent to user %s device %s", user_id, row.device_id)
        except Exception as exc:
            code = getattr(exc, "code", "") or ""
            if code in {"registration-token-not-registered", "invalid-registration-token"}:
                row.is_active = False
                db.flush()
            logger.warning("FCM send failed for device %s: %s", row.device_id, exc)
    if commit_changes and (sent or rows):
        db.commit()
    return sent


def send_test_push_to_user(*, db: Session, user_id: str) -> dict:
    status = push_service_status(db=db, user_id=user_id)
    sent = send_push_to_user(
        db=db,
        user_id=user_id,
        title="African Beauty test",
        body="Push notifications are connected on this device.",
        data={"type": "push_test"},
    )
    return {**status, "sent": sent}
