"""Provides the Availability business logic module for booking workflows."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from core.enumeration import BookingStatus
from models.booking.booking import Booking
from models.profile.salon import (
    Salon,
    SalonAvailabilityOverride,
    SalonServicePrice,
    SalonWorkingHour,
)
from pydantic_schemas.availability import AvailabilityOverrideIn
from service.account.enforcement import salon_booking_rules_for_salon


TZ_EAT = timezone(timedelta(hours=3))
SLOT_STEP_MINUTES = 15


def upsert_availability_override(
    *,
    db: Session,
    salon_id: str,
    payload: AvailabilityOverrideIn,
) -> SalonAvailabilityOverride:
    row = (
        db.query(SalonAvailabilityOverride)
        .filter(
            SalonAvailabilityOverride.salon_id == salon_id,
            SalonAvailabilityOverride.date == payload.date,
        )
        .first()
    )
    if row is None:
        row = SalonAvailabilityOverride(salon_id=salon_id, date=payload.date)
        db.add(row)

    row.is_closed = payload.is_closed
    row.open_time = None if payload.is_closed else payload.open_time
    row.close_time = None if payload.is_closed else payload.close_time
    row.reason = payload.reason
    db.commit()
    db.refresh(row)
    return row


def list_availability_overrides(
    *,
    db: Session,
    salon_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[SalonAvailabilityOverride]:
    query = db.query(SalonAvailabilityOverride).filter(
        SalonAvailabilityOverride.salon_id == salon_id,
    )
    if start_date:
        query = query.filter(SalonAvailabilityOverride.date >= start_date)
    if end_date:
        query = query.filter(SalonAvailabilityOverride.date <= end_date)
    return query.order_by(SalonAvailabilityOverride.date.asc()).all()


def delete_availability_override(*, db: Session, salon_id: str, override_id: str) -> None:
    row = (
        db.query(SalonAvailabilityOverride)
        .filter(
            SalonAvailabilityOverride.id == override_id,
            SalonAvailabilityOverride.salon_id == salon_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Availability override not found")
    db.delete(row)
    db.commit()


def get_slots_for_service(
    *,
    db: Session,
    salon_service_price_id: str,
    target_date: date,
) -> dict:
    offering = (
        db.query(SalonServicePrice)
        .options(joinedload(SalonServicePrice.salon))
        .filter(SalonServicePrice.id == salon_service_price_id)
        .first()
    )
    if not offering:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service offering not found")

    schedule = _schedule_for_date(db=db, salon_id=offering.salon_id, target_date=target_date)
    if schedule["closed"]:
        return {
            "date": target_date,
            "salon_service_price_id": salon_service_price_id,
            "is_open": False,
            "reason": schedule["reason"],
            "slots": [],
        }

    duration = offering.duration_minutes or 60
    capacity = offering.concurrent_capacity or 1
    open_dt = _local_datetime(target_date, schedule["open_time"])
    close_dt = _local_datetime(target_date, schedule["close_time"])
    rules = salon_booking_rules_for_salon(db, offering.salon_id)
    now_utc = datetime.now(timezone.utc) + timedelta(hours=rules.minimum_notice_hours)

    slots = []
    cursor = open_dt
    while cursor + timedelta(minutes=duration) <= close_dt:
      start_utc = cursor.astimezone(timezone.utc)
      end_utc = (cursor + timedelta(minutes=duration)).astimezone(timezone.utc)
      if start_utc > now_utc:
          booked = _overlap_count(
              db=db,
              salon_service_price_id=salon_service_price_id,
              start_at=start_utc,
              end_at=end_utc,
              buffer_minutes=rules.buffer_minutes,
          )
          remaining = max(capacity - booked, 0)
          if remaining > 0:
              slots.append({
                  "start_at": start_utc,
                  "end_at": end_utc,
                  "remaining_capacity": remaining,
              })
      cursor += timedelta(minutes=rules.slot_interval_minutes or SLOT_STEP_MINUTES)

    return {
        "date": target_date,
        "salon_service_price_id": salon_service_price_id,
        "is_open": True,
        "reason": schedule["reason"],
        "slots": slots,
    }


def ensure_booking_time_available(
    *,
    db: Session,
    offering: SalonServicePrice,
    start_at: datetime,
    end_at: datetime,
) -> None:
    local_start = start_at.astimezone(TZ_EAT)
    local_end = end_at.astimezone(TZ_EAT)
    rules = salon_booking_rules_for_salon(db, offering.salon_id)
    if start_at < datetime.now(timezone.utc) + timedelta(hours=rules.minimum_notice_hours):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Booking must be at least {rules.minimum_notice_hours} hours from now",
        )
    schedule = _schedule_for_date(
        db=db,
        salon_id=offering.salon_id,
        target_date=local_start.date(),
    )
    if schedule["closed"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, schedule["reason"] or "Salon is closed on this date")

    open_dt = _local_datetime(local_start.date(), schedule["open_time"])
    close_dt = _local_datetime(local_start.date(), schedule["close_time"])
    if local_start < open_dt or local_end > close_dt:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected time is outside salon availability")


def _schedule_for_date(*, db: Session, salon_id: str, target_date: date) -> dict:
    override = (
        db.query(SalonAvailabilityOverride)
        .filter(
            SalonAvailabilityOverride.salon_id == salon_id,
            SalonAvailabilityOverride.date == target_date,
        )
        .first()
    )
    if override:
        if override.is_closed:
            return {"closed": True, "reason": override.reason or "Salon is closed", "open_time": None, "close_time": None}
        return {
            "closed": False,
            "reason": override.reason,
            "open_time": override.open_time,
            "close_time": override.close_time,
        }

    weekday = target_date.weekday()
    working_hour = (
        db.query(SalonWorkingHour)
        .filter(
            SalonWorkingHour.salon_id == salon_id,
            SalonWorkingHour.day_of_week == weekday,
        )
        .first()
    )
    if not working_hour or not working_hour.is_open:
        return {"closed": True, "reason": "Salon is closed", "open_time": None, "close_time": None}
    return {
        "closed": False,
        "reason": None,
        "open_time": working_hour.open_time,
        "close_time": working_hour.close_time,
    }


def _local_datetime(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=TZ_EAT)


def _overlap_count(
    *,
    db: Session,
    salon_service_price_id: str,
    start_at: datetime,
    end_at: datetime,
    buffer_minutes: int = 0,
) -> int:
    buffer_delta = timedelta(minutes=max(buffer_minutes or 0, 0))
    return db.query(Booking).filter(
        Booking.salon_service_price_id == salon_service_price_id,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        Booking.start_at < end_at + buffer_delta,
        Booking.end_at > start_at - buffer_delta,
    ).count()
