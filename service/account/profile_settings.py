"""Provides the Profile Settings business logic module for account workflows."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.auth.user import User
from pydantic_schemas.account.profile_settings import (
    AccountDataExport,
    CustomerBeautyPreferences,
    CustomerBlockedAccounts,
    CustomerProfilePreviewVisibility,
    CustomerRecommendationControls,
    SalonBookingRules,
    SalonCampaignDraft,
    SalonCampaignDrafts,
    SalonCampaignHistory,
    SalonCampaignHistoryItem,
    SalonTeamPermissions,
)
from service.account.settings import get_account_settings, update_account_settings
from pydantic_schemas.account.settings import AccountSettingsUpdate


T = TypeVar("T", bound=BaseModel)

CUSTOMER_BEAUTY_KEY = "customer_beauty_preferences"
CUSTOMER_RECOMMENDATION_KEY = "customer_recommendation_controls"
CUSTOMER_PREVIEW_KEY = "customer_profile_preview_visibility"
CUSTOMER_BLOCKED_KEY = "customer_blocked_accounts"
SALON_BOOKING_RULES_KEY = "salon_booking_rules"
SALON_CAMPAIGN_DRAFTS_KEY = "salon_campaign_drafts"
SALON_CAMPAIGN_HISTORY_KEY = "salon_campaign_history"
SALON_TEAM_PERMISSIONS_KEY = "salon_team_permissions"


def _settings(db: Session, user_id: str) -> dict[str, Any]:
    return dict(get_account_settings(db, user_id).get("settings") or {})


def _save(db: Session, user_id: str, key: str, value: Any) -> dict:
    return update_account_settings(
        db,
        user_id,
        AccountSettingsUpdate(settings={key: value}),
    )


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _coerce(model: type[T], raw: Any, aliases: dict[str, str] | None = None) -> T:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    if aliases:
        for old, new in aliases.items():
            if old in data and new not in data:
                data[new] = data[old]
    return model(**data)


def _ensure_salon_owner(user: User) -> None:
    role = (user.role or "").strip().lower()
    if role not in {"service", "salon", "salon_owner", "owner"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Salon owner permission required",
        )


def get_customer_beauty_preferences(db: Session, user_id: str) -> CustomerBeautyPreferences:
    return _coerce(
        CustomerBeautyPreferences,
        _settings(db, user_id).get(CUSTOMER_BEAUTY_KEY),
        {
            "budgetMin": "budget_min",
            "budgetMax": "budget_max",
            "radiusKm": "radius_km",
            "preferredArea": "preferred_area",
        },
    )


def update_customer_beauty_preferences(
    db: Session,
    user_id: str,
    payload: CustomerBeautyPreferences,
) -> CustomerBeautyPreferences:
    _save(db, user_id, CUSTOMER_BEAUTY_KEY, _dump(payload))
    update_account_settings(
        db,
        user_id,
        AccountSettingsUpdate(
            settings={
                "customer_settings_nearbyDiscovery": True,
                "customer_settings_personalizedRecommendations": True,
            }
        ),
    )
    return payload


def get_customer_recommendation_controls(
    db: Session,
    user_id: str,
) -> CustomerRecommendationControls:
    return _coerce(
        CustomerRecommendationControls,
        _settings(db, user_id).get(CUSTOMER_RECOMMENDATION_KEY),
        {
            "useSaved": "use_saved",
            "useFollowing": "use_following",
            "useBookings": "use_bookings",
            "useLocation": "use_location",
            "showTrending": "show_trending",
            "showPromotions": "show_promotions",
        },
    )


def update_customer_recommendation_controls(
    db: Session,
    user_id: str,
    payload: CustomerRecommendationControls,
) -> CustomerRecommendationControls:
    _save(db, user_id, CUSTOMER_RECOMMENDATION_KEY, _dump(payload))
    update_account_settings(
        db,
        user_id,
        AccountSettingsUpdate(
            settings={
                "customer_settings_personalizedRecommendations": (
                    payload.use_saved or payload.use_following or payload.use_bookings
                ),
                "customer_settings_nearbyDiscovery": payload.use_location,
            }
        ),
    )
    return payload


def get_customer_profile_preview_visibility(
    db: Session,
    user_id: str,
) -> CustomerProfilePreviewVisibility:
    settings = _settings(db, user_id)
    model = _coerce(
        CustomerProfilePreviewVisibility,
        settings.get(CUSTOMER_PREVIEW_KEY),
        {"bookingActivity": "booking_activity"},
    )
    return model.model_copy(
        update={
            "audience": settings.get("customer_three_dots_shareAudience", model.audience),
            "discoverable": settings.get(
                "customer_settings_profileDiscoverable",
                model.discoverable,
            ),
        }
    )


def update_customer_profile_preview_visibility(
    db: Session,
    user_id: str,
    payload: CustomerProfilePreviewVisibility,
) -> CustomerProfilePreviewVisibility:
    update_account_settings(
        db,
        user_id,
        AccountSettingsUpdate(
            settings={
                CUSTOMER_PREVIEW_KEY: _dump(payload),
                "customer_three_dots_shareAudience": payload.audience,
                "customer_settings_profileDiscoverable": payload.discoverable,
            }
        ),
    )
    return payload


def get_customer_blocked_accounts(db: Session, user_id: str) -> CustomerBlockedAccounts:
    raw = _settings(db, user_id).get(CUSTOMER_BLOCKED_KEY)
    if isinstance(raw, list):
        return CustomerBlockedAccounts(accounts=[str(item) for item in raw])
    return _coerce(CustomerBlockedAccounts, raw)


def update_customer_blocked_accounts(
    db: Session,
    user_id: str,
    payload: CustomerBlockedAccounts,
) -> CustomerBlockedAccounts:
    deduped = list(dict.fromkeys(item.strip() for item in payload.accounts if item.strip()))
    result = CustomerBlockedAccounts(accounts=deduped)
    _save(db, user_id, CUSTOMER_BLOCKED_KEY, result.accounts)
    return result


def get_salon_booking_rules(db: Session, user: User) -> SalonBookingRules:
    _ensure_salon_owner(user)
    return _coerce(
        SalonBookingRules,
        _settings(db, user.id).get(SALON_BOOKING_RULES_KEY),
        {
            "minimumNoticeHours": "minimum_notice_hours",
            "cancelWindowHours": "cancel_window_hours",
            "slotIntervalMinutes": "slot_interval_minutes",
            "bufferMinutes": "buffer_minutes",
            "autoConfirm": "auto_confirm",
            "allowCustomerNotes": "allow_customer_notes",
        },
    )


def update_salon_booking_rules(
    db: Session,
    user: User,
    payload: SalonBookingRules,
) -> SalonBookingRules:
    _ensure_salon_owner(user)
    _save(db, user.id, SALON_BOOKING_RULES_KEY, _dump(payload))
    return payload


def get_salon_campaign_drafts(db: Session, user: User) -> SalonCampaignDrafts:
    _ensure_salon_owner(user)
    raw = _settings(db, user.id).get(SALON_CAMPAIGN_DRAFTS_KEY)
    if isinstance(raw, list):
        return SalonCampaignDrafts(drafts=[SalonCampaignDraft(**dict(item)) for item in raw if isinstance(item, dict)])
    return _coerce(SalonCampaignDrafts, raw)


def update_salon_campaign_drafts(
    db: Session,
    user: User,
    payload: SalonCampaignDrafts,
) -> SalonCampaignDrafts:
    _ensure_salon_owner(user)
    now = datetime.now(timezone.utc)
    drafts = [
        draft.model_copy(
            update={
                "id": draft.id or str(uuid.uuid4()),
                "created_at": draft.created_at or now,
            }
        )
        for draft in payload.drafts
    ]
    result = SalonCampaignDrafts(drafts=drafts)
    _save(db, user.id, SALON_CAMPAIGN_DRAFTS_KEY, [_dump(item) for item in drafts])
    return result


def get_salon_campaign_history(db: Session, user: User) -> SalonCampaignHistory:
    _ensure_salon_owner(user)
    raw = _settings(db, user.id).get(SALON_CAMPAIGN_HISTORY_KEY)
    if isinstance(raw, list):
        return SalonCampaignHistory(history=[SalonCampaignHistoryItem(**dict(item)) for item in raw if isinstance(item, dict)])
    return _coerce(SalonCampaignHistory, raw)


def update_salon_campaign_history(
    db: Session,
    user: User,
    payload: SalonCampaignHistory,
) -> SalonCampaignHistory:
    _ensure_salon_owner(user)
    now = datetime.now(timezone.utc)
    history = [
        item.model_copy(
            update={
                "id": item.id or str(uuid.uuid4()),
                "sent_at": item.sent_at or now,
            }
        )
        for item in payload.history
    ]
    result = SalonCampaignHistory(history=history)
    _save(db, user.id, SALON_CAMPAIGN_HISTORY_KEY, [_dump(item) for item in history])
    return result


def get_salon_team_permissions(db: Session, user: User) -> SalonTeamPermissions:
    _ensure_salon_owner(user)
    return _coerce(SalonTeamPermissions, _settings(db, user.id).get(SALON_TEAM_PERMISSIONS_KEY))


def update_salon_team_permissions(
    db: Session,
    user: User,
    payload: SalonTeamPermissions,
) -> SalonTeamPermissions:
    _ensure_salon_owner(user)
    _save(db, user.id, SALON_TEAM_PERMISSIONS_KEY, _dump(payload))
    return payload


def get_customer_account_data_export(db: Session, user: User) -> AccountDataExport:
    settings = {
        key: value
        for key, value in _settings(db, user.id).items()
        if key.startswith("customer_")
    }
    return AccountDataExport(
        exported_at=datetime.now(timezone.utc),
        profile={
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "created_at": user.created_at,
        },
        customer_settings=settings,
    )
