import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_

from core.database import SessionLocal
from core.enumeration import Status
from models.auth.verification import Verification
from models.booking.booking import Booking, BookingStatus
from models.profile.notification_preferences import UserNotificationPreference
from service.auth.send_code import mail_send
from service.profile.top_salon import get_top_salons
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="worker.tasks.send_verification_email", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_verification_email(code: str, email: str) -> dict:
    asyncio.run(mail_send(code=code, email=email))
    return {"email": email, "sent": True}


@celery_app.task(name="worker.tasks.send_push_notification")
def send_push_notification(
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> dict:
    # Device-token storage and provider integration come next. Keeping this as
    # a task gives API code a stable boundary before FCM/OneSignal is added.
    logger.info(
        "push notification queued for user_id=%s title=%s data=%s",
        user_id,
        title,
        data or {},
    )
    return {"user_id": user_id, "sent": False, "reason": "push provider not configured"}


@celery_app.task(name="worker.tasks.cleanup_expired_auth_records")
def cleanup_expired_auth_records() -> dict:
    db = SessionLocal()
    try:
        now = datetime.now()
        expired_verifications = (
            db.query(Verification)
            .filter(
                Verification.status == Status.PENDING,
                Verification.expires_at.isnot(None),
                Verification.expires_at < now,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"expired_verifications_deleted": expired_verifications}
    except Exception:
        db.rollback()
        logger.exception("cleanup_expired_auth_records failed")
        raise
    finally:
        db.close()


@celery_app.task(name="worker.tasks.refresh_top_salon_ranking")
def refresh_top_salon_ranking(limit: int = 100) -> dict:
    db = SessionLocal()
    try:
        result = get_top_salons(db=db, limit=limit)
        # There is no ranking cache table yet, so this warms and validates the
        # ranking query. Persisting the score snapshot should be the next schema
        # step once product ranking rules settle.
        count = len(result.get("results", []))
        logger.info("refreshed top salon ranking candidates=%s", count)
        return {"ranked_salons": count}
    finally:
        db.close()


@celery_app.task(name="worker.tasks.scan_booking_reminders")
def scan_booking_reminders(window_minutes: int = 60) -> dict:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=window_minutes)

        rows = (
            db.query(Booking)
            .outerjoin(
                UserNotificationPreference,
                UserNotificationPreference.user_id == Booking.customer_id,
            )
            .filter(
                Booking.status == BookingStatus.CONFIRMED,
                Booking.start_at >= now,
                Booking.start_at <= window_end,
                or_(
                    UserNotificationPreference.id.is_(None),
                    UserNotificationPreference.allow_reminders.is_(True),
                ),
            )
            .all()
        )

        # A durable "reminder sent" marker is needed before this task should
        # create notifications or push messages; otherwise Celery Beat would
        # duplicate reminders every run.
        logger.info("booking reminder candidates=%s", len(rows))
        return {"reminder_candidates": len(rows), "sent": 0}
    finally:
        db.close()
