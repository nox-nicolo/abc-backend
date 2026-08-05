"""Provides the Enforcement business logic module for account workflows."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.account.settings import UserAccountSettings
from models.auth.user import User
from models.profile.salon import Salon
from pydantic_schemas.account.profile_settings import (
    CustomerProfilePreviewVisibility,
    CustomerRecommendationControls,
    SalonBookingRules,
    SalonTeamPermissions,
)
from pydantic_schemas.customer.profile import CustomerProfileResponse, CustomerStatsSchema
from service.account.profile_settings import (
    CUSTOMER_BLOCKED_KEY,
    CUSTOMER_PREVIEW_KEY,
    CUSTOMER_RECOMMENDATION_KEY,
    SALON_BOOKING_RULES_KEY,
    SALON_TEAM_PERMISSIONS_KEY,
)


def account_settings_for_user(db: Session, user_id: str | None) -> dict[str, Any]:
    if not user_id:
        return {}
    row = (
        db.query(UserAccountSettings.settings)
        .filter(UserAccountSettings.user_id == user_id)
        .first()
    )
    return dict(row.settings or {}) if row else {}


def customer_preview_visibility(db: Session, user_id: str) -> CustomerProfilePreviewVisibility:
    settings = account_settings_for_user(db, user_id)
    raw = settings.get(CUSTOMER_PREVIEW_KEY)
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    if "bookingActivity" in data and "booking_activity" not in data:
        data["booking_activity"] = data["bookingActivity"]
    model = CustomerProfilePreviewVisibility(**data)
    return model.model_copy(
        update={
            "audience": settings.get("customer_three_dots_shareAudience", model.audience),
            "discoverable": settings.get("customer_settings_profileDiscoverable", model.discoverable),
        }
    )


def customer_recommendation_controls(db: Session, user_id: str) -> CustomerRecommendationControls:
    raw = account_settings_for_user(db, user_id).get(CUSTOMER_RECOMMENDATION_KEY)
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    aliases = {
        "useSaved": "use_saved",
        "useFollowing": "use_following",
        "useBookings": "use_bookings",
        "useLocation": "use_location",
        "showTrending": "show_trending",
        "showPromotions": "show_promotions",
    }
    for old, new in aliases.items():
        if old in data and new not in data:
            data[new] = data[old]
    return CustomerRecommendationControls(**data)


def salon_booking_rules_for_salon(db: Session, salon_id: str) -> SalonBookingRules:
    salon = db.query(Salon.user_id).filter(Salon.id == salon_id).first()
    if not salon:
        return SalonBookingRules()
    raw = account_settings_for_user(db, salon.user_id).get(SALON_BOOKING_RULES_KEY)
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    aliases = {
        "minimumNoticeHours": "minimum_notice_hours",
        "cancelWindowHours": "cancel_window_hours",
        "slotIntervalMinutes": "slot_interval_minutes",
        "bufferMinutes": "buffer_minutes",
        "autoConfirm": "auto_confirm",
        "allowCustomerNotes": "allow_customer_notes",
    }
    for old, new in aliases.items():
        if old in data and new not in data:
            data[new] = data[old]
    return SalonBookingRules(**data)


def booking_buffer_delta(db: Session, salon_id: str) -> timedelta:
    return timedelta(minutes=salon_booking_rules_for_salon(db, salon_id).buffer_minutes)


def enforce_salon_team_permission(db: Session, user_id: str, action: str) -> None:
    raw = account_settings_for_user(db, user_id).get(SALON_TEAM_PERMISSIONS_KEY)
    permissions = SalonTeamPermissions(**(dict(raw or {}) if isinstance(raw, dict) else {}))
    values = permissions.permissions
    allowed = values.get(action)
    if allowed is None:
        allowed = values.get("team", {}).get(action, True)
    elif isinstance(allowed, dict):
        allowed = allowed.get("enabled", True)
    if allowed is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This salon team action is disabled by team permissions",
        )


def blocked_identifiers(db: Session, user_id: str | None) -> set[str]:
    settings = account_settings_for_user(db, user_id)
    raw = settings.get(CUSTOMER_BLOCKED_KEY)
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, dict):
        values = raw.get("accounts") or []
    else:
        values = []
    return {str(item).strip().lower() for item in values if str(item).strip()}


def user_matches_identifiers(user: User | None, identifiers: set[str]) -> bool:
    if not user or not identifiers:
        return False
    candidates = {
        str(user.id or "").lower(),
        str(user.username or "").lower(),
        str(user.name or "").lower(),
        str(user.email or "").lower(),
        str(user.phone or "").lower(),
    }
    return bool(candidates & identifiers)


def is_blocked_between(db: Session, viewer_user_id: str | None, target_user_id: str | None) -> bool:
    if not viewer_user_id or not target_user_id or viewer_user_id == target_user_id:
        return False
    viewer = db.query(User).filter(User.id == viewer_user_id).first()
    target = db.query(User).filter(User.id == target_user_id).first()
    return user_matches_identifiers(target, blocked_identifiers(db, viewer_user_id)) or user_matches_identifiers(
        viewer,
        blocked_identifiers(db, target_user_id),
    )


def apply_customer_profile_visibility(
    *,
    db: Session,
    profile: CustomerProfileResponse,
    target_user_id: str,
    viewer_user_id: str | None,
) -> CustomerProfileResponse:
    if viewer_user_id == target_user_id:
        return profile
    if is_blocked_between(db, viewer_user_id, target_user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    visibility = customer_preview_visibility(db, target_user_id)
    if visibility.audience == "Only me":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    return profile.model_copy(
        update={
            "profile_picture": profile.profile_picture if visibility.photo else None,
            "bio": profile.bio if visibility.bio else None,
            "city": profile.city if visibility.city else None,
            "country": profile.country if visibility.city else None,
            "preferred_services": profile.preferred_services if visibility.saved else [],
            "stats": CustomerStatsSchema(
                following_count=profile.stats.following_count if visibility.following else 0,
                bookings_count=profile.stats.bookings_count if visibility.booking_activity else 0,
                reviews_count=profile.stats.reviews_count if visibility.booking_activity else 0,
            ),
        }
    )


def can_discover_customer(db: Session, target_user_id: str, viewer_user_id: str | None) -> bool:
    if viewer_user_id == target_user_id:
        return True
    if is_blocked_between(db, viewer_user_id, target_user_id):
        return False
    visibility = customer_preview_visibility(db, target_user_id)
    return visibility.discoverable and visibility.audience != "Only me"
