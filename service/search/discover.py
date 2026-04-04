from __future__ import annotations

from datetime import datetime, timezone, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageDirectories
from core.r2_config import BASE_URL
from models.auth.user import User
from models.booking.booking import Booking
from models.posts.posts import Hashtag, PostHashtag
from models.profile.salon import Salon, SalonLocation

_profile_url = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"
_salon_url = f"{BASE_URL}/{ImageDirectories.SALON_COVER_DIR.value}"


def _cover(salon: Salon) -> str | None:
    if salon.display_ads and salon.display_ads != "Not Set":
        return _salon_url + salon.display_ads
    if salon.user and salon.user.profile_picture:
        return _profile_url + salon.user.profile_picture.file_name
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
) -> List[dict]:
    # Bounding-box pre-filter (1 degree ≈ 111 km)
    delta = radius_km / 111.0
    candidates = (
        db.query(Salon)
        .join(SalonLocation, SalonLocation.salon_id == Salon.id)
        .options(
            joinedload(Salon.user).joinedload(User.profile_picture),
            joinedload(Salon.location),
        )
        .filter(
            SalonLocation.latitude.isnot(None),
            SalonLocation.longitude.isnot(None),
            SalonLocation.latitude.between(lat - delta, lat + delta),
            SalonLocation.longitude.between(lng - delta, lng + delta),
        )
        .all()
    )

    results = []
    for salon in candidates:
        loc = salon.location
        if not loc or loc.latitude is None or loc.longitude is None:
            continue
        dist = _haversine_km(lat, lng, loc.latitude, loc.longitude)
        if dist <= radius_km:
            results.append({
                "id": salon.id,
                "title": salon.title or "",
                "cover_image": _cover(salon),
                "city": loc.city,
                "distance_km": round(dist, 1),
            })

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


# ── Top salons (by booking count) ─────────────────────────────────────────────

def get_top_salons(
    db: Session,
    current_user_id: str,
    limit: int = 10,
) -> List[dict]:
    rows = (
        db.query(Salon, func.count(Booking.id).label("booking_count"))
        .outerjoin(Booking, Booking.salon_id == Salon.id)
        .options(
            joinedload(Salon.user).joinedload(User.profile_picture),
            joinedload(Salon.location),
        )
        .filter(Salon.user_id != current_user_id)
        .group_by(Salon.id)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": salon.id,
            "title": salon.title or "",
            "cover_image": _cover(salon),
            "city": salon.location.city if salon.location else None,
            "booking_count": booking_count,
        }
        for salon, booking_count in rows
    ]


# ── Trending styles (hashtags in last 30 days) ────────────────────────────────

def get_trending_styles(db: Session, limit: int = 10) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (
        db.query(Hashtag, func.count(PostHashtag.id).label("post_count"))
        .join(PostHashtag, PostHashtag.hashtag_id == Hashtag.id)
        .filter(PostHashtag.created_at >= since)
        .group_by(Hashtag.id)
        .order_by(func.count(PostHashtag.id).desc())
        .limit(limit)
        .all()
    )
    return [{"id": h.id, "tag": h.name, "post_count": count} for h, count in rows]
