"""Provides the Availability Calendar business logic module for profile workflows."""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.profile.salon import Salon, SalonAvailabilityOverride
from pydantic_schemas.profile.settings import SalonAvailabilityOverrideIn


def _get_owner_salon(db: Session, user_id: str) -> Salon:
    salon = db.query(Salon).filter(Salon.user_id == user_id).first()
    if not salon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Salon not found")
    return salon


async def list_availability_overrides_(
    *,
    user_id: str,
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    salon = _get_owner_salon(db, user_id)
    query = db.query(SalonAvailabilityOverride).filter(
        SalonAvailabilityOverride.salon_id == salon.id,
    )
    if start_date:
        query = query.filter(SalonAvailabilityOverride.date >= start_date)
    if end_date:
        query = query.filter(SalonAvailabilityOverride.date <= end_date)

    return {
        "items": query.order_by(SalonAvailabilityOverride.date.asc()).all(),
    }


async def upsert_availability_override_(
    *,
    user_id: str,
    payload: SalonAvailabilityOverrideIn,
    db: Session,
) -> SalonAvailabilityOverride:
    salon = _get_owner_salon(db, user_id)
    override = (
        db.query(SalonAvailabilityOverride)
        .filter(
            SalonAvailabilityOverride.salon_id == salon.id,
            SalonAvailabilityOverride.date == payload.date,
        )
        .first()
    )

    if override is None:
        override = SalonAvailabilityOverride(
            salon_id=salon.id,
            date=payload.date,
        )
        db.add(override)

    override.is_closed = payload.is_closed
    override.open_time = None if payload.is_closed else payload.open_time
    override.close_time = None if payload.is_closed else payload.close_time
    override.reason = payload.reason

    db.commit()
    db.refresh(override)
    return override


async def delete_availability_override_(
    *,
    user_id: str,
    override_id: str,
    db: Session,
) -> None:
    salon = _get_owner_salon(db, user_id)
    override = (
        db.query(SalonAvailabilityOverride)
        .filter(
            SalonAvailabilityOverride.id == override_id,
            SalonAvailabilityOverride.salon_id == salon.id,
        )
        .first()
    )
    if not override:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Availability override not found")

    db.delete(override)
    db.commit()
