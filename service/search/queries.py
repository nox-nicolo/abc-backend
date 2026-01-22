# service/search/queries.py

from __future__ import annotations

import re
from typing import List

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from core.enumeration import ImageURL
from models.auth.user import User
from models.posts.posts import Hashtag
from models.profile.salon import Salon, SalonServicePrice
from models.services.service import Services, SubServices

from pydantic_schemas.search.search import (
    SearchHashtagResult,
    SearchSalonResult,
    SearchServiceResult,
    SearchUserResult,
)

from service.search.scoring import (
    compute_user_score,
    compute_salon_score,
    compute_hashtag_score,
    compute_service_score,
)

profile_url = ImageURL.PROFILE_URL.value
major_url = ImageURL.SERVICE_URL.value + "major/"
minor_url = ImageURL.SERVICE_URL.value + "minor/"


# ---------------------------
# Helpers (price parsing)
# ---------------------------

def extract_price(q: str) -> int | None:
    """
    Extract number from:
    '30', '30k', 'under 40', '50,000', 'braids 30k'
    """
    raw = q.replace(",", "").lower()
    m = re.search(r"(\d+)", raw)
    if not m:
        return None

    value = int(m.group(1))
    if "k" in raw:
        value *= 1000
    return value


def is_price_only_query(q: str) -> bool:
    """
    price-only means: contains digits AND does not contain letters.
    So:
    - "30k" -> letters exist ('k') => not price-only by this strict definition,
      but it's still price intent. We'll treat it as price-only if it contains no real words.
    We'll implement a better check below.
    """
    raw = q.strip().lower()
    if extract_price(raw) is None:
        return False

    # treat "30k" as price-only too
    # price-only if no alphabetic sequences longer than 1 char (like 'under', 'braids')
    words = re.findall(r"[a-z]+", raw)
    if not words:
        return True
    # allow single-letter like 'k'
    return all(len(w) == 1 for w in words)


def clean_query(q: str) -> str:
    return (q or "").strip()


def safe_parent_service_name(sub: SubServices) -> str | None:
    """
    Your project may name the relationship 'service' or 'services'.
    This prevents attribute errors.
    """
    parent = getattr(sub, "service", None) or getattr(sub, "services", None)
    return getattr(parent, "name", None)


# ---------------------------
# Users
# ---------------------------

def search_users(db: Session, q: str, limit: int, current_user_id: str) -> List[SearchUserResult]:
    q_clean = clean_query(q)
    if not q_clean:
        return []

    users = (
        db.query(User)
        .options(joinedload(User.profile_picture))
        .filter(
            or_(
                User.username.ilike(f"%{q_clean}%"),
                func.coalesce(User.name, "").ilike(f"%{q_clean}%"),
            )
        )
        .limit(limit)
        .all()
    )

    results: List[SearchUserResult] = []
    for user in users:
        if user.id == current_user_id:
            continue

        avatar_url = (profile_url + user.profile_picture.file_name) if user.profile_picture else None
        score = compute_user_score(user.username, user.name, q_clean)

        results.append(
            SearchUserResult(
                id=user.id,
                entity="user",
                username=user.username,
                full_name=user.name,
                avatar_url=avatar_url,
                score=score,
            )
        )

    return results


# ---------------------------
# Salons
# ---------------------------

def search_salons(db: Session, q: str, limit: int, current_user_id: str) -> List[SearchSalonResult]:
    q_clean = clean_query(q)
    if not q_clean:
        return []

    salons = (
        db.query(Salon)
        .options(joinedload(Salon.user))  # salon owner
        .filter(
            or_(
                func.coalesce(Salon.slogan, "").ilike(f"%{q_clean}%"),
                func.coalesce(Salon.title, "").ilike(f"%{q_clean}%"),
            )
        )
        .limit(limit)
        .all()
    )

    results: List[SearchSalonResult] = []
    for salon in salons:
        # exclude own salon (Salon.user_id is owner user id)
        if salon.user_id == current_user_id:
            continue

        is_verified = bool(salon.user.is_verified) if salon.user else False
        owner_name = salon.user.name if salon.user else None

        score = compute_salon_score(salon.title, salon.slogan, q_clean, is_verified)

        results.append(
            SearchSalonResult(
                id=salon.id,
                entity="salon",
                name=getattr(salon, "name", salon.title),  # if your schema requires `name`
                title=salon.title,
                cover_image=salon.display_ads,
                is_verified=is_verified,
                owner_name=owner_name,
                slogan=salon.slogan,
                score=score,
            )
        )

    return results


# ---------------------------
# Hashtags
# ---------------------------

def search_hashtags(db: Session, q: str, limit: int) -> List[SearchHashtagResult]:
    q_clean = clean_query(q)
    if not q_clean:
        return []

    hashtags = (
        db.query(Hashtag)
        .options(joinedload(Hashtag.post_hashtags))
        .filter(Hashtag.name.ilike(f"%{q_clean}%"))
        .limit(limit)
        .all()
    )

    results: List[SearchHashtagResult] = []
    for hashtag in hashtags:
        post_count = len(hashtag.post_hashtags or [])
        score = compute_hashtag_score(hashtag.name, q_clean, post_count)

        results.append(
            SearchHashtagResult(
                id=hashtag.id,
                entity="hashtag",
                tag=hashtag.name,
                post_count=post_count,
                score=score,
            )
        )

    return results


# ---------------------------
# Services (priced + fallback)
# ---------------------------

def search_services(db: Session, q: str, limit: int, current_user_id: str) -> List[SearchServiceResult]:
    results: List[SearchServiceResult] = []

    q_clean = clean_query(q)
    if not q_clean:
        return results

    target_price = extract_price(q_clean)
    price_only = is_price_only_query(q_clean)

    # -------------------------------
    # 1) PRICED SERVICES
    # -------------------------------
    priced_q = (
        db.query(SalonServicePrice)
        .join(Salon, SalonServicePrice.salon_id == Salon.id)
        .options(
            joinedload(SalonServicePrice.service),
            joinedload(SalonServicePrice.sub_service),
        )
        .outerjoin(Services, SalonServicePrice.service_id == Services.id)
        .outerjoin(SubServices, SalonServicePrice.sub_service_id == SubServices.id)
        .filter(Salon.user_id != current_user_id)  # exclude own salon offerings
    )

    # Name filter only when not price-only
    if not price_only:
        priced_q = priced_q.filter(
            or_(
                Services.name.ilike(f"%{q_clean}%"),
                SubServices.name.ilike(f"%{q_clean}%"),
            )
        )

    # Price filter
    if target_price is not None:
        priced_q = priced_q.filter(
            or_(
                # price_max present and <= target
                and_(SalonServicePrice.price_max.isnot(None), SalonServicePrice.price_max <= target_price),
                # open-ended max: allow if min <= target
                and_(SalonServicePrice.price_max.is_(None), SalonServicePrice.price_min.isnot(None), SalonServicePrice.price_min <= target_price),
                # if only max exists (rare)
                and_(SalonServicePrice.price_min.is_(None), SalonServicePrice.price_max.isnot(None), SalonServicePrice.price_max <= target_price),
            )
        )

    prices = priced_q.limit(limit).all()

    if prices:
        for row in prices:
            # Minor priced result
            if row.sub_service:
                parent_name = safe_parent_service_name(row.sub_service)

                score = compute_service_score(
                    name=row.sub_service.name,
                    q=q_clean,
                    category="minor",
                    is_priced=True,
                    target_price=target_price,
                    price_min=row.price_min,
                    price_max=row.price_max,
                )

                results.append(
                    SearchServiceResult(
                        id=row.id,
                        entity="service",
                        service_name=row.sub_service.name,
                        category="minor",
                        parent_service_name=parent_name,
                        price_min=row.price_min,
                        price_max=row.price_max,
                        image_url=minor_url + row.sub_service.file_name,
                        score=score,
                    )
                )

            # Major priced result
            elif row.service:
                score = compute_service_score(
                    name=row.service.name,
                    q=q_clean,
                    category="major",
                    is_priced=True,
                    target_price=target_price,
                    price_min=row.price_min,
                    price_max=row.price_max,
                )

                results.append(
                    SearchServiceResult(
                        id=row.id,
                        entity="service",
                        service_name=row.service.name,
                        category="major",
                        parent_service_name=None,
                        price_min=row.price_min,
                        price_max=row.price_max,
                        image_url=major_url + row.service.service_picture,
                        score=score,
                    )
                )

        return results

    # -------------------------------
    # 2) FALLBACK (ONLY if no price intent)
    # -------------------------------
    if target_price is not None:
        # user asked for price and none found => return empty (correct UX)
        return []

    # Major service fallback
    services = (
        db.query(Services)
        .filter(Services.name.ilike(f"%{q_clean}%"))
        .limit(limit)
        .all()
    )
    for service in services:
        score = compute_service_score(
            name=service.name,
            q=q_clean,
            category="major",
            is_priced=False,
            target_price=None,
            price_min=None,
            price_max=None,
        )
        results.append(
            SearchServiceResult(
                id=service.id,
                entity="service",
                service_name=service.name,
                category="major",
                parent_service_name=None,
                price_min=None,
                price_max=None,
                image_url=major_url + service.service_picture,
                score=score,
            )
        )

    # Minor service fallback
    sub_services = (
        db.query(SubServices)
        .join(Services)
        .filter(SubServices.name.ilike(f"%{q_clean}%"))
        .limit(limit)
        .all()
    )
    for sub in sub_services:
        parent_name = safe_parent_service_name(sub)

        score = compute_service_score(
            name=sub.name,
            q=q_clean,
            category="minor",
            is_priced=False,
            target_price=None,
            price_min=None,
            price_max=None,
        )
        results.append(
            SearchServiceResult(
                id=sub.id,
                entity="service",
                service_name=sub.name,
                category="minor",
                parent_service_name=parent_name,
                price_min=None,
                price_max=None,
                image_url=minor_url + sub.file_name,
                score=score,
            )
        )

    return results
