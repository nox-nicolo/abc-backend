"""Provides the Profile Completion business logic module for account workflows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.auth.customer_profile import CustomerProfile
from models.auth.user import User
from models.profile.salon import (
    Salon,
    SalonContact,
    SalonGallery,
    SalonLocation,
    SalonServicePrice,
    SalonWorkingHour,
)
from pydantic_schemas.account.profile_completion import (
    ProfileCompletionItem,
    ProfileCompletionResponse,
)
from service.account.settings import get_account_settings
from service.auth.permissions import normalize_role


def get_profile_completion(db: Session, user: User) -> ProfileCompletionResponse:
    role = normalize_role(user.role)
    if role == "salon_owner":
        return _salon_completion(db, user)
    return _customer_completion(db, user)


def _settings(db: Session, user_id: str) -> dict:
    return dict(get_account_settings(db, user_id).get("settings") or {})


def _has_text(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _security_enabled(settings: dict, prefix: str, user: User) -> bool:
    return (
        bool(settings.get(f"{prefix}_account_security_two_step_enabled"))
        or bool(settings.get(f"{prefix}_account_security_login_alerts", True))
        or bool(user.is_verified)
    )


def _response(
    *,
    role: str,
    title: str,
    subtitle: str,
    items: list[ProfileCompletionItem],
) -> ProfileCompletionResponse:
    total_weight = sum(item.weight for item in items) or 1
    done_weight = sum(item.weight for item in items if item.completed)
    score = round((done_weight / total_weight) * 100)
    return ProfileCompletionResponse(
        role=role,
        score=score,
        completed=sum(1 for item in items if item.completed),
        total=len(items),
        title=title,
        subtitle=subtitle,
        items=items,
    )


def _customer_completion(db: Session, user: User) -> ProfileCompletionResponse:
    settings = _settings(db, user.id)
    profile = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.user_id == user.id)
        .first()
    )
    beauty = settings.get("customer_beauty_preferences") or {}
    recommendations = settings.get("customer_recommendation_controls") or {}

    has_preferences = bool(beauty.get("styles")) or bool(beauty.get("services"))
    has_recommendations = any(
        recommendations.get(key, False)
        for key in (
            "use_saved",
            "use_following",
            "use_bookings",
            "use_location",
            "show_trending",
            "show_promotions",
        )
    )

    items = [
        ProfileCompletionItem(
            key="profile_photo",
            title="Profile photo added",
            subtitle="Add a clear photo so salons recognize your account.",
            completed=user.profile_picture is not None,
        ),
        ProfileCompletionItem(
            key="bio",
            title="Bio completed",
            subtitle="Add a short note about your beauty style.",
            completed=profile is not None and _has_text(profile.bio),
        ),
        ProfileCompletionItem(
            key="location",
            title="Location set",
            subtitle="City and country help improve nearby salon discovery.",
            completed=profile is not None
            and (_has_text(profile.city) or _has_text(profile.country)),
        ),
        ProfileCompletionItem(
            key="beauty_preferences",
            title="Beauty preferences configured",
            subtitle="Choose styles, services, budget, and discovery radius.",
            completed=has_preferences,
        ),
        ProfileCompletionItem(
            key="recommendations",
            title="Recommendation controls configured",
            subtitle="Decide which signals can personalize discovery.",
            completed=has_recommendations,
        ),
        ProfileCompletionItem(
            key="security",
            title="Security enabled",
            subtitle="Keep login alerts or verification enabled.",
            completed=_security_enabled(settings, "customer", user),
        ),
    ]
    return _response(
        role="customer",
        title="Customer profile strength",
        subtitle="Complete your profile so salons can serve you better.",
        items=items,
    )


def _salon_completion(db: Session, user: User) -> ProfileCompletionResponse:
    settings = _settings(db, user.id)
    salon = db.query(Salon).filter(Salon.user_id == user.id).first()

    if salon is None:
        items = [
            ProfileCompletionItem(
                key="salon_profile",
                title="Salon profile created",
                subtitle="Create your salon profile to unlock business tools.",
                completed=False,
            )
        ]
        return _response(
            role="salon",
            title="Salon profile strength",
            subtitle="Create your salon profile to start tracking completion.",
            items=items,
        )

    has_contact = (
        db.query(SalonContact.id)
        .filter(SalonContact.salon_id == salon.id)
        .first()
        is not None
    )
    has_location = (
        db.query(SalonLocation.id)
        .filter(SalonLocation.salon_id == salon.id)
        .first()
        is not None
    )
    has_services = (
        db.query(SalonServicePrice.id)
        .filter(SalonServicePrice.salon_id == salon.id)
        .first()
        is not None
    )
    has_gallery = (
        db.query(SalonGallery.id)
        .filter(SalonGallery.salon_id == salon.id)
        .first()
        is not None
    )
    has_hours = (
        db.query(SalonWorkingHour.id)
        .filter(
            SalonWorkingHour.salon_id == salon.id,
            SalonWorkingHour.is_open == True,
        )
        .first()
        is not None
    )
    has_booking_rules = bool(settings.get("salon_booking_rules"))

    items = [
        ProfileCompletionItem(
            key="profile_photo",
            title="Profile photo added",
            subtitle="Add a salon logo or clear storefront profile image.",
            completed=user.profile_picture is not None,
        ),
        ProfileCompletionItem(
            key="bio",
            title="Bio completed",
            subtitle="Add salon description, slogan, and specialty details.",
            completed=_has_text(salon.description) or _has_text(salon.slogan),
        ),
        ProfileCompletionItem(
            key="location",
            title="Location set",
            subtitle="Add address, map location, and contact information.",
            completed=has_location and has_contact,
        ),
        ProfileCompletionItem(
            key="services",
            title="Services added",
            subtitle="Create services with prices and durations.",
            completed=has_services,
            weight=2,
        ),
        ProfileCompletionItem(
            key="gallery",
            title="Gallery added",
            subtitle="Upload salon visuals customers can inspect.",
            completed=has_gallery,
        ),
        ProfileCompletionItem(
            key="working_hours",
            title="Working hours configured",
            subtitle="Set open days and customer-facing hours.",
            completed=has_hours,
        ),
        ProfileCompletionItem(
            key="booking_rules",
            title="Booking rules configured",
            subtitle="Set notice, cancellation window, slot interval, and workflow.",
            completed=has_booking_rules,
        ),
        ProfileCompletionItem(
            key="security",
            title="Security enabled",
            subtitle="Keep owner login alerts or verification enabled.",
            completed=_security_enabled(settings, "salon", user),
        ),
    ]
    return _response(
        role="salon",
        title="Salon profile strength",
        subtitle="Complete your salon setup to improve trust and booking readiness.",
        items=items,
    )
