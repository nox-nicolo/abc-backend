import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from core.database import SessionLocal
from core.enumeration import Status
from models.auth.verification import Verification
from models.booking.booking import Booking, BookingStatus
from models.auth.user import User
from models.profile.salon import Salon
from models.profile.notification_preferences import UserNotificationPreference
from service.auth.send_code import mail_send
from service.notification.booking_ai import (
    MAX_REMINDERS_PER_CYCLE,
    BookingNotificationContext,
    EventBookingNotificationContext,
    booking_link,
    generate_booking_message,
    generate_event_based_booking_message,
    generate_rebooking_reminder_message,
    is_allowed_send_time,
    rebooking_cycle_weeks,
    rebooking_link,
)
from service.notification.notification import (
    count_sends_for_cycle,
    create_notification,
    log_notification_send,
)
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
def scan_booking_reminders(window_minutes: int = 120) -> dict:
    db = SessionLocal()
    try:
        if not is_allowed_send_time():
            logger.info("booking reminder scan skipped outside Tanzania send window")
            return {"reminder_candidates": 0, "sent": 0, "skipped_reason": "outside_send_window"}

        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=window_minutes)

        rows = (
            db.query(Booking)
            .options(
                joinedload(Booking.customer).joinedload(User.profile_picture),
                joinedload(Booking.salon).joinedload(Salon.user),
            )
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

        sent = 0
        skipped_already_sent = 0
        skipped_not_due = 0

        for booking in rows:
            if not booking.salon:
                continue

            pref = (
                db.query(UserNotificationPreference)
                .filter(UserNotificationPreference.user_id == booking.customer_id)
                .first()
            )
            lead_minutes = pref.reminder_lead_minutes if pref else 30
            minutes_until_start = (booking.start_at - now).total_seconds() / 60
            if minutes_until_start < 0 or minutes_until_start > lead_minutes:
                skipped_not_due += 1
                continue

            cycle_key = f"booking_reminder:{booking.id}:lead:{lead_minutes}"
            send_count = count_sends_for_cycle(
                db=db,
                recipient_id=booking.customer_id,
                cycle_key=cycle_key,
                type="booking_reminder_ai",
            )
            if send_count >= 1:
                skipped_already_sent += 1
                continue

            local_start = booking.start_at.astimezone(timezone(timedelta(hours=3)))
            message = generate_booking_message(
                BookingNotificationContext(
                    customer_name=booking.customer.name if booking.customer else "there",
                    service_type=booking.service_name_snapshot or "your service",
                    salon_name=booking.salon.title,
                    booking_date=local_start.strftime("%b %d"),
                    booking_time=local_start.strftime("%H:%M"),
                    booking_link=booking_link(booking.id),
                    reminder_number=1,
                )
            )

            notification = create_notification(
                db=db,
                recipient_id=booking.customer_id,
                actor_id=booking.salon.user_id,
                type="booking_reminder_ai",
                booking_id=booking.id,
                message=message,
                commit=False,
            )
            log_notification_send(
                db=db,
                recipient_id=booking.customer_id,
                actor_id=booking.salon.user_id,
                notification_id=notification.id if notification else None,
                booking_id=booking.id,
                type="booking_reminder_ai",
                cycle_key=cycle_key,
                message=message,
            )
            sent += 1

        db.commit()
        logger.info("booking reminder candidates=%s sent=%s", len(rows), sent)
        return {
            "reminder_candidates": len(rows),
            "sent": sent,
            "skipped_already_sent": skipped_already_sent,
            "skipped_not_due": skipped_not_due,
        }
    except Exception:
        db.rollback()
        logger.exception("scan_booking_reminders failed")
        raise
    finally:
        db.close()


@celery_app.task(name="worker.tasks.scan_rebooking_reminders")
def scan_rebooking_reminders(lookback_days: int = 180) -> dict:
    db = SessionLocal()
    try:
        if not is_allowed_send_time():
            logger.info("rebooking reminder scan skipped outside Tanzania send window")
            return {"candidates": 0, "sent": 0, "skipped_reason": "outside_send_window"}

        now = datetime.now(timezone.utc)
        oldest = now - timedelta(days=lookback_days)
        rows = (
            db.query(Booking)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.salon).joinedload(Salon.user),
            )
            .outerjoin(
                UserNotificationPreference,
                UserNotificationPreference.user_id == Booking.customer_id,
            )
            .filter(
                Booking.status == BookingStatus.COMPLETED,
                Booking.end_at >= oldest,
                Booking.end_at <= now,
                or_(
                    UserNotificationPreference.id.is_(None),
                    UserNotificationPreference.allow_reminders.is_(True),
                ),
            )
            .all()
        )

        sent = 0
        skipped_limit = 0
        skipped_not_due = 0
        skipped_rebooked = 0

        for booking in rows:
            if not booking.salon or not booking.salon.user_id:
                continue

            cycle_key = f"rebooking:{booking.id}"
            send_count = count_sends_for_cycle(
                db=db,
                recipient_id=booking.customer_id,
                cycle_key=cycle_key,
                type="rebooking_reminder_ai",
            )
            if send_count >= MAX_REMINDERS_PER_CYCLE:
                skipped_limit += 1
                continue

            cycle_weeks = rebooking_cycle_weeks(booking.service_name_snapshot)
            due_at = booking.end_at + timedelta(weeks=cycle_weeks + send_count)
            if now < due_at:
                skipped_not_due += 1
                continue

            if _customer_has_rebooked_service(db=db, booking=booking):
                skipped_rebooked += 1
                continue

            weeks_since_last_visit = max(1, (now - booking.end_at).days // 7)
            payload = generate_rebooking_reminder_message(
                BookingNotificationContext(
                    customer_name=booking.customer.name if booking.customer else "there",
                    service_type=booking.service_name_snapshot or "your service",
                    salon_name=booking.salon.title,
                    booking_date="",
                    booking_time="",
                    booking_link=rebooking_link(booking.id),
                    weeks_since_last_visit=weeks_since_last_visit,
                    reminder_number=send_count + 1,
                )
            )
            message = payload["message"]

            notification = create_notification(
                db=db,
                recipient_id=booking.customer_id,
                actor_id=booking.salon.user_id,
                type="rebooking_reminder_ai",
                booking_id=booking.id,
                message=message,
                commit=False,
            )
            log_notification_send(
                db=db,
                recipient_id=booking.customer_id,
                actor_id=booking.salon.user_id,
                notification_id=notification.id if notification else None,
                booking_id=booking.id,
                type="rebooking_reminder_ai",
                cycle_key=cycle_key,
                message=message,
            )
            sent += 1

        db.commit()
        logger.info("rebooking reminder candidates=%s sent=%s", len(rows), sent)
        return {
            "candidates": len(rows),
            "sent": sent,
            "skipped_limit": skipped_limit,
            "skipped_not_due": skipped_not_due,
            "skipped_rebooked": skipped_rebooked,
        }
    except Exception:
        db.rollback()
        logger.exception("scan_rebooking_reminders failed")
        raise
    finally:
        db.close()


def _customer_has_rebooked_service(*, db, booking: Booking) -> bool:
    if not booking.salon_service_price_id:
        return False
    return (
        db.query(Booking.id)
        .filter(
            Booking.id != booking.id,
            Booking.customer_id == booking.customer_id,
            Booking.salon_service_price_id == booking.salon_service_price_id,
            Booking.start_at > booking.end_at,
            Booking.status.in_([
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.COMPLETED,
            ]),
        )
        .first()
        is not None
    )


@celery_app.task(name="worker.tasks.send_event_based_booking_notification")
def send_event_based_booking_notification(
    recipient_id: str,
    actor_id: Optional[str],
    customer_name: str,
    upcoming_event: str,
    days_until_event: int,
    salon_name: str,
    service_type: str,
    booking_link: str,
    stylist_name: Optional[str] = None,
) -> dict:
    db = SessionLocal()
    try:
        if days_until_event < 0 or days_until_event > 21:
            return {
                "sent": False,
                "skipped_reason": "event_outside_three_week_window",
            }

        if not is_allowed_send_time():
            return {"sent": False, "skipped_reason": "outside_send_window"}

        payload = generate_event_based_booking_message(
            EventBookingNotificationContext(
                customer_name=customer_name,
                upcoming_event=upcoming_event,
                days_until_event=days_until_event,
                salon_name=salon_name,
                stylist_name=stylist_name,
                service_type=service_type,
                booking_link=booking_link,
            )
        )

        notification = create_notification(
            db=db,
            recipient_id=recipient_id,
            actor_id=actor_id,
            type="event_based_booking",
            message=payload["message"],
            commit=False,
        )
        log_notification_send(
            db=db,
            recipient_id=recipient_id,
            actor_id=actor_id,
            notification_id=notification.id if notification else None,
            type="event_based_booking",
            cycle_key=f"event_based:{recipient_id}:{upcoming_event}:{days_until_event}",
            message=payload["message"],
        )
        db.commit()
        return {
            "sent": True,
            "channel": payload["channel"],
            "trigger": payload["trigger"],
        }
    except Exception:
        db.rollback()
        logger.exception("send_event_based_booking_notification failed")
        raise
    finally:
        db.close()
