import logging
import os
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from models.notifications.device_token import UserDeviceToken

logger = logging.getLogger("abc.push")


@lru_cache(maxsize=1)
def _firebase_app():
    credentials_path = os.getenv("FIREBASE_ADMIN_CREDENTIALS") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        logger.info("FCM disabled: FIREBASE_ADMIN_CREDENTIALS is not set")
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
        cred = credentials.Certificate(credentials_path)
        return firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("FCM initialization failed")
        return None


def send_push_to_user(
    *,
    db: Session,
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict[str, str]] = None,
) -> int:
    app = _firebase_app()
    if app is None:
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
    sent = 0
    for row in rows:
        message = messaging.Message(
            token=row.push_token,
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
        )
        try:
            messaging.send(message, app=app)
            sent += 1
        except Exception as exc:
            code = getattr(exc, "code", "") or ""
            if code in {"registration-token-not-registered", "invalid-registration-token"}:
                row.is_active = False
                db.flush()
            logger.warning("FCM send failed for device %s: %s", row.device_id, exc)
    if sent or rows:
        db.commit()
    return sent
