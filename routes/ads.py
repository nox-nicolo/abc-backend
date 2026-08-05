"""Provides the Ads API route module for the backend application."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.ads import AdCampaignCreate, AdCampaignOut, AdEventRequest, AdListResponse
from pydantic_schemas.auth.jwt_token import TokenData
from service.ads import create_ad_campaign, record_ad_event, select_ads
from service.auth.JWT.oauth2 import get_current_user

ads = APIRouter(prefix="/ads", tags=["Ads"])


@ads.get("", response_model=AdListResponse)
def list_ads_for_placement(
    placement: str = Query(..., pattern="^(home_feed|search|post_view)$"),
    limit: int = Query(1, ge=1, le=5),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return select_ads(
        db=db,
        placement=placement,
        limit=limit,
        country=country,
        city=city,
        category_id=category_id,
    )


@ads.post("", response_model=AdCampaignOut, status_code=201)
def create_ad(
    payload: AdCampaignCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return create_ad_campaign(db=db, user_id=current_user.user_id, payload=payload)


@ads.post("/{ad_id}/impression")
def ad_impression(
    ad_id: str,
    payload: AdEventRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return record_ad_event(
        db=db,
        ad_id=ad_id,
        event_type="impression",
        placement=payload.placement,
        user_id=current_user.user_id,
    )


@ads.post("/{ad_id}/click")
def ad_click(
    ad_id: str,
    payload: AdEventRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return record_ad_event(
        db=db,
        ad_id=ad_id,
        event_type="click",
        placement=payload.placement,
        user_id=current_user.user_id,
    )
