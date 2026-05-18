from __future__ import annotations

from datetime import datetime, timezone, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.booking.booking import Booking
from models.posts.posts import Post
from models.profile.salon import Salon, SalonLocation
from models.services.service import SubServices
from pydantic_schemas.pagination import pagination_meta

_salon_url = f"{BASE_URL}/{ImageDirectories.SALON_COVER_DIR.value}"
_minor_url = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}minor/"


def _cover_from_row(display_ads, profile_file_name=None) -> str | None:
    if display_ads:
        return _salon_url + display_ads
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


# ── Nearby salons ─────────────────────────────────────────────────────────────

def get_nearby_salons(
    db: Session,
    lat: float,
    lng: float,
    radius_km: float = 15.0,
    limit: int = 10,
    offset: int = 0,
    current_user_id: str | None = None,
) -> dict:
    lat_delta = radius_km / 111.0
    lng_degrees_per_km = max(abs(111.320 * cos(radians(lat))), 0.01)
    lng_delta = radius_km / lng_degrees_per_km

    query = (
        db.query(
            Salon.id,
            Salon.title,
            Salon.display_ads,
            SalonLocation.city,
            SalonLocation.latitude,
            SalonLocation.longitude,
            ProfilePicture.file_name.label("profile_file"),
        )
        .join(SalonLocation, SalonLocation.salon_id == Salon.id)
        .join(User, User.id == Salon.user_id)
        .outerjoin(ProfilePicture, ProfilePicture.user_id == User.id)
        .filter(
            SalonLocation.latitude.isnot(None),
            SalonLocation.longitude.isnot(None),
            SalonLocation.latitude.between(lat - lat_delta, lat + lat_delta),
            SalonLocation.longitude.between(lng - lng_delta, lng + lng_delta),
        )
    )

    rows = query.all()

    results = []
    for row in rows:
        if row.latitude is None or row.longitude is None:
            continue
        dist = _haversine_km(lat, lng, row.latitude, row.longitude)
        if dist <= radius_km:
            results.append({
                "id": row.id,
                "title": row.title or "",
                "cover_image": _cover_from_row(row.display_ads, row.profile_file),
                "city": row.city,
                "distance_km": round(dist, 1),
                "lat": row.latitude,
                "lng": row.longitude,
            })

    results.sort(key=lambda x: x["distance_km"])
    if not results:
        fallback_rows = (
            db.query(
                Salon.id,
                Salon.title,
                Salon.display_ads,
                SalonLocation.city,
                SalonLocation.latitude,
                SalonLocation.longitude,
                ProfilePicture.file_name.label("profile_file"),
            )
            .join(SalonLocation, SalonLocation.salon_id == Salon.id)
            .join(User, User.id == Salon.user_id)
            .outerjoin(ProfilePicture, ProfilePicture.user_id == User.id)
            .filter(
                SalonLocation.latitude.isnot(None),
                SalonLocation.longitude.isnot(None),
            )
            .all()
        )
        for row in fallback_rows:
            if row.latitude is None or row.longitude is None:
                continue
            dist = _haversine_km(lat, lng, row.latitude, row.longitude)
            results.append({
                "id": row.id,
                "title": row.title or "",
                "cover_image": _cover_from_row(row.display_ads, row.profile_file),
                "city": row.city,
                "distance_km": round(dist, 1),
                "lat": row.latitude,
                "lng": row.longitude,
            })
        results.sort(key=lambda x: x["distance_km"])

    total = len(results)
    return {
        "items": results[offset: offset + limit],
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


# ── Top salons (by booking count) ─────────────────────────────────────────────

def get_top_salons(
    db: Session,
    current_user_id: str,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    # Use a flat column query — avoids joinedload conflict with group_by aggregates
    query = (
        db.query(
            Salon.id,
            Salon.title,
            Salon.display_ads,
            SalonLocation.city,
            ProfilePicture.file_name.label("profile_file"),
            func.count(Booking.id).label("booking_count"),
        )
        .outerjoin(Booking, Booking.salon_id == Salon.id)
        .join(User, User.id == Salon.user_id)
        .outerjoin(ProfilePicture, ProfilePicture.user_id == User.id)
        .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
        .group_by(
            Salon.id,
            Salon.title,
            Salon.display_ads,
            SalonLocation.city,
            ProfilePicture.file_name,
        )
        .order_by(func.count(Booking.id).desc())
    )
    total = query.count()
    rows = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": row.id,
            "title": row.title or "",
            "cover_image": _cover_from_row(row.display_ads, row.profile_file),
            "city": row.city,
            "booking_count": row.booking_count,
        }
        for row in rows
    ]
    return {
        "items": items,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


# ── Trending styles (sub-services by recent post count) ───────────────────────

def get_trending_styles(db: Session, limit: int = 10, offset: int = 0) -> dict:
    """Returns the most-posted sub-services in the last 30 days with their images."""
    since = datetime.now(timezone.utc) - timedelta(days=30)

    query = (
        db.query(
            SubServices.id,
            SubServices.name,
            SubServices.file_name,
            func.count(Post.id).label("post_count"),
        )
        .join(Post, Post.sub_service_id == SubServices.id)
        .filter(Post.created_at >= since)
        .group_by(SubServices.id, SubServices.name, SubServices.file_name)
        .order_by(func.count(Post.id).desc())
    )
    total = query.count()
    rows = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": row.id,
            "name": row.name,
            "image": (_minor_url + row.file_name) if row.file_name else None,
            "post_count": row.post_count,
        }
        for row in rows
    ]
    return {
        "items": items,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }
