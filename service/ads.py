"""Provides the Ads business logic module for the backend application."""

from __future__ import annotations

from datetime import datetime, timezone
from random import random
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from models.ads import AdCampaign, AdEvent
from models.auth.user import User
from pydantic_schemas.ads import AdCampaignCreate


def _is_admin(user: User | None) -> bool:
    return (user.role or "").lower() in {"admin", "super_admin"} if user else False


def _as_out(ad: AdCampaign) -> dict:
    return {
        "id": ad.id,
        "advertiser_name": ad.advertiser_name,
        "title": ad.title,
        "body": ad.body,
        "cta_label": ad.cta_label,
        "destination_url": ad.destination_url,
        "media_url": ad.media_url,
        "media_type": ad.media_type,
        "placement": ad.placement,
        "priority": ad.priority,
        "sponsored_label": "Sponsored",
    }


def create_ad_campaign(db: Session, user_id: str, payload: AdCampaignCreate) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not _is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create ad campaigns.",
        )

    campaign = AdCampaign(
        id=str(uuid.uuid4()),
        advertiser_name=payload.advertiser_name,
        title=payload.title,
        body=payload.body,
        cta_label=payload.cta_label,
        destination_url=str(payload.destination_url),
        media_url=str(payload.media_url),
        media_type=payload.media_type,
        placement=payload.placement,
        status=payload.status,
        priority=payload.priority,
        weight=payload.weight,
        target_country=payload.target_country,
        target_city=payload.target_city,
        target_category_id=payload.target_category_id,
        target_is_required=payload.target_is_required,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        max_impressions=payload.max_impressions,
        max_clicks=payload.max_clicks,
        created_by_user_id=user_id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _as_out(campaign)


def select_ads(
    db: Session,
    placement: str,
    limit: int = 1,
    country: str | None = None,
    city: str | None = None,
    category_id: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)

    query = db.query(AdCampaign).filter(
        AdCampaign.status == "active",
        AdCampaign.placement == placement,
        or_(AdCampaign.starts_at.is_(None), AdCampaign.starts_at <= now),
        or_(AdCampaign.ends_at.is_(None), AdCampaign.ends_at >= now),
        or_(AdCampaign.max_impressions.is_(None), AdCampaign.impression_count < AdCampaign.max_impressions),
        or_(AdCampaign.max_clicks.is_(None), AdCampaign.click_count < AdCampaign.max_clicks),
    )

    candidates = query.all()
    ranked = []
    for ad in candidates:
        geo_match = _target_matches(ad.target_country, country) and _target_matches(ad.target_city, city)
        category_match = _target_matches(ad.target_category_id, category_id)

        if ad.target_is_required and not (geo_match and category_match):
            continue

        score = ad.priority * 10 + ad.weight + random()
        if ad.target_country and _target_matches(ad.target_country, country):
            score += 8
        if ad.target_city and _target_matches(ad.target_city, city):
            score += 12
        if ad.target_category_id and _target_matches(ad.target_category_id, category_id):
            score += 10

        ranked.append((score, ad))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return {"items": [_as_out(ad) for _, ad in ranked[:limit]]}


def record_ad_event(
    db: Session,
    ad_id: str,
    event_type: str,
    placement: str,
    user_id: str | None,
) -> dict:
    if event_type not in {"impression", "click"}:
        raise HTTPException(status_code=400, detail="Unsupported ad event type.")

    ad = db.query(AdCampaign).filter(AdCampaign.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad campaign not found.")

    event = AdEvent(
        id=str(uuid.uuid4()),
        ad_id=ad_id,
        user_id=user_id,
        event_type=event_type,
        placement=placement,
    )
    db.add(event)
    if event_type == "impression":
        ad.impression_count += 1
    if event_type == "click":
        ad.click_count += 1

    db.commit()
    return {"ok": True}


def _target_matches(target: str | None, actual: str | None) -> bool:
    if not target:
        return True
    if not actual:
        return False
    return target.strip().lower() == actual.strip().lower()
