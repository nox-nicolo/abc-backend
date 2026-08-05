"""Provides the Ratings business logic module for booking workflows."""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.booking.booking import ServiceReview


def _rating_summary(query) -> dict:
    avg_rating, count = query.with_entities(
        func.avg(ServiceReview.rating),
        func.count(ServiceReview.id),
    ).one()
    return {
        "average": round(float(avg_rating), 2) if avg_rating is not None else 0.0,
        "count": int(count or 0),
    }


def salon_rating_summary(db: Session, *, salon_id: str) -> dict:
    return _rating_summary(
        db.query(ServiceReview).filter(ServiceReview.salon_id == salon_id)
    )


def stylist_rating_summary(db: Session, *, stylist_id: str) -> dict:
    return _rating_summary(
        db.query(ServiceReview).filter(ServiceReview.stylist_id == stylist_id)
    )


def sub_service_rating_summary(
    db: Session,
    *,
    sub_service_id: str,
    salon_id: Optional[str] = None,
) -> dict:
    query = db.query(ServiceReview).filter(ServiceReview.sub_service_id == sub_service_id)
    if salon_id is not None:
        query = query.filter(ServiceReview.salon_id == salon_id)
    return _rating_summary(query)


def service_rating_summary(
    db: Session,
    *,
    service_id: str,
    salon_id: Optional[str] = None,
) -> dict:
    query = db.query(ServiceReview).filter(ServiceReview.service_id == service_id)
    if salon_id is not None:
        query = query.filter(ServiceReview.salon_id == salon_id)
    return _rating_summary(query)
