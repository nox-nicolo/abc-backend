"""Provides the Notifications API route module for the backend application."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.notifications.notification import (
    NotificationListResponse,
    SalonEventCampaignRequest,
    SalonEventCampaignResponse,
    SalonPromotionCampaignRequest,
    SalonPromotionCampaignResponse,
    UnreadCountResponse,
)
from service.auth.JWT.oauth2 import get_current_user
from service.auth.permissions import SalonPrincipal, require_salon_owner
from service.notification.notification import (
    clear_notifications,
    create_salon_event_campaign,
    create_salon_promotion_campaign,
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_read,
)


notifications = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications.get("", response_model=NotificationListResponse)
def get_notifications(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_notifications(
        db=db,
        user_id=current_user.user_id,
        cursor=cursor,
        limit=limit,
    )


@notifications.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_unread_count(db=db, user_id=current_user.user_id)


@notifications.post(
    "/salon/event-campaign",
    response_model=SalonEventCampaignResponse,
    status_code=201,
)
def create_event_campaign(
    payload: SalonEventCampaignRequest,
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
    db: Session = Depends(get_db),
):
    return create_salon_event_campaign(
        db=db,
        owner_user_id=salon_owner.user_id,
        payload=payload,
    )


@notifications.post(
    "/salon/promotion-campaign",
    response_model=SalonPromotionCampaignResponse,
    status_code=201,
)
def create_promotion_campaign(
    payload: SalonPromotionCampaignRequest,
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
    db: Session = Depends(get_db),
):
    return create_salon_promotion_campaign(
        db=db,
        owner_user_id=salon_owner.user_id,
        payload=payload,
    )


@notifications.post("/read", status_code=200)
def read_all(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mark_all_read(db=db, user_id=current_user.user_id)


@notifications.delete("", status_code=200)
def clear_all_notifications(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return clear_notifications(db=db, user_id=current_user.user_id)


@notifications.post("/{notification_id}/read", status_code=200)
def read_one(
    notification_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mark_read(
        db=db,
        user_id=current_user.user_id,
        notification_id=notification_id,
    )
