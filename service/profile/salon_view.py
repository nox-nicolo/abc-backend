# from datetime import datetime, timezone
# from fastapi import HTTPException
# from sqlalchemy.orm import Session, joinedload
# from sqlalchemy import func

# from core.enumeration import ImageURL
# from models.auth.user import User
# from models.auth.profile_picture import ProfilePicture
# from models.posts.posts import Post
from models.booking.booking import ServiceReview
# from models.saved import SavedSalon
# from models.profile.salon import (
#     Salon,
#     SalonFollower,
#     SalonBlock,
# #     SalonServicePrice,
#     SalonStylist,
#     StylistService,
# )


# PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value
# COVER_IMAGE_BASE = ImageURL.SALON_COVER_URL.value
# SALON_GALLERY_BASE = ImageURL.SALON_GALLERY_URL.value


# # -------------------------------------------------------------------
# # Public / Viewer Salon Profile
# # -------------------------------------------------------------------
# async def view_salon_profile(
#     *,
#     db: Session,
#     salon_id: str,
#     viewer_id: str | None,
# ):
#     # ───────────────── Salon (core) ─────────────────
#     salon: Salon | None = (
#         db.query(Salon)
#         .options(
#             joinedload(Salon.user),
#             joinedload(Salon.contacts),
#             joinedload(Salon.working_hours),
#             joinedload(Salon.location),
#             joinedload(Salon.galleries),
#         )
#         .filter(Salon.id == salon_id)
#         .first()
#     )

#     if not salon:
#         raise HTTPException(status_code=404, detail="Salon not found")

#     owner: User = salon.user

#     # ───────────────── Viewer state ─────────────────
#     is_following = False
#     notifications_enabled = False
#     is_blocked = False

#     if viewer_id:
#         follow = (
#             db.query(SalonFollower)
#             .filter(
#                 SalonFollower.salon_id == salon.id,
#                 SalonFollower.user_id == viewer_id,
#             )
#             .first()
#         )

#         if follow:
#             is_following = True
#             notifications_enabled = follow.notifications_enabled

#         is_blocked = (
#             db.query(SalonBlock)
#             .filter(
#                 SalonBlock.salon_id == salon.id,
#                 SalonBlock.user_id == viewer_id,
#             )
#             .first()
#             is not None
#         )

#     # ───────────────── Profile & cover images ─────────────────
#     profile_picture = (
#         db.query(ProfilePicture)
#         .filter(ProfilePicture.user_id == owner.id)
#         .first()
#     )

#     profile_picture_url = (
#         f"{PROFILE_IMAGE_BASE}{profile_picture.file_name}"
#         if profile_picture
#         else None
#     )

#     cover_image_url = (
#         f"{COVER_IMAGE_BASE}{salon.display_ads}"
#         if salon.display_ads
#         else None
#     )

#     # ───────────────── Gallery ─────────────────
#     gallery_items = []
#     for index, g in enumerate(
#         sorted(salon.galleries, key=lambda x: x.created_at), start=1
#     ):
#         gallery_items.append(
#             {
#                 "id": g.id,
#                 "image_url": f"{SALON_GALLERY_BASE}{g.file_name}",
#                 "order": index,
#             }
#         )

#     # ───────────────── Metrics ─────────────────
#     followers_count = (
#         db.query(func.count(SalonFollower.id))
#         .filter(SalonFollower.salon_id == salon.id)
#         .scalar()
#         or 0
#     )

#     posts_count = (
#         db.query(func.count(Post.id))
#         .filter(Post.user_id == salon.user_id)
#         .scalar()
#         or 0
#     )

#     rating_avg = (
#         db.query(func.avg(Rate.value))
#         .filter(Rate.salon_id == salon.id)
#         .scalar()
#     )

#     reviews_count = (
#         db.query(func.count(Rate.id))
#         .filter(Rate.salon_id == salon.id)
#         .scalar()
#         or 0
#     )

#     # ───────────────── Availability ─────────────────
#     now = datetime.now(timezone.utc)
#     today_weekday = now.weekday()

#     today_wh = next(
#         (wh for wh in salon.working_hours if wh.day_of_week == today_weekday),
#         None,
#     )

#     is_open_now = False
#     today_data = None

#     if today_wh and today_wh.is_open and today_wh.open_time and today_wh.close_time:
#         current_time = now.time()
#         if today_wh.open_time <= current_time <= today_wh.close_time:
#             is_open_now = True

#         today_data = {
#             "day": today_wh.day_of_week,
#             "open_time": today_wh.open_time.strftime("%H:%M"),
#             "close_time": today_wh.close_time.strftime("%H:%M"),
#         }

#     weekly = []
#     for wh in sorted(salon.working_hours, key=lambda x: x.day_of_week):
#         weekly.append(
#             {
#                 "day": wh.day_of_week,
#                 "is_open": wh.is_open,
#                 "open": wh.open_time.strftime("%H:%M") if wh.open_time else None,
#                 "close": wh.close_time.strftime("%H:%M") if wh.close_time else None,
#             }
#         )

#     # ───────────────── Contacts ─────────────────
#     contacts_map = {c.type: c.value for c in salon.contacts}

#     location = None
#     if salon.location:
#         location = {
#             "address": " ".join(
#                 filter(
#                     None,
#                     [
#                         salon.location.street,
#                         salon.location.city,
#                         salon.location.region,
#                         salon.location.country,
#                     ],
#                 )
#             ),
#             "lat": salon.location.latitude,
#             "lng": salon.location.longitude,
#         }
        
    
#     # ───────────────── Services ─────────────────
#     service_prices = (
#         db.query(SalonServicePrice)
#         .options(
#             joinedload(SalonServicePrice.service),
#             joinedload(SalonServicePrice.sub_service),
#             joinedload(SalonServicePrice.benefits),
#             joinedload(SalonServicePrice.products),
#             joinedload(SalonServicePrice.bookings),
#             joinedload(SalonServicePrice.reviews),
#         )
#         .filter(SalonServicePrice.salon_id == salon.id)
#         .all()
#     )
    
#     stylist_map = {}

#     stylist_services = (
#         db.query(StylistService)
#         .join(SalonStylist)
#         .join(User)
#         .options(
#             joinedload(StylistService.stylist).joinedload(SalonStylist.user)
#         )
#         .filter(SalonStylist.salon_id == salon.id)
#         .all()
#     )

#     for ss in stylist_services:
#         stylist_map.setdefault(ss.salon_service_price_id, []).append(
#             {
#                 "id": ss.stylist.id,
#                 "name": ss.stylist.user.name,
#                 "avatar": (
#                     f"{PROFILE_IMAGE_BASE}{ss.stylist.user.profile_picture.file_name}"
#                     if ss.stylist.user.profile_picture
#                     else None
#                 ),
#             }
#         )
        
#     services_by_category = {}

#     for sp in service_prices:
#         if not sp.service:
#             continue

#         cat_id = sp.service.id
#         cat_name = sp.service.name

#         services_by_category.setdefault(cat_id, {
#             "category_id": cat_id,
#             "category_name": cat_name,
#             "services": [],
#         })

#         services_by_category[cat_id]["services"].append(
#             {
#                 "id": sp.id,
#                 "category_id": cat_id,
#                 "category_name": cat_name,
#                 "sub_service_id": sp.sub_service.id if sp.sub_service else None,
#                 "name": sp.sub_service.name if sp.sub_service else cat_name,
#                 "image": None,  # optional: later from service/sub_service media
#                 "price_min": sp.price_min,
#                 "price_max": sp.price_max,
#                 "currency": sp.currency,
#                 "duration_minutes": sp.duration_minutes,
#                 "stylists": stylist_map.get(sp.id, []),
#             }
#         )




#     # ───────────────── Final response ─────────────────
#     return {
#         "salon": {
#             "id": salon.id,
#             "username": owner.username,
#             "name": salon.title,
#             "slogan": salon.slogan,
#             "description": salon.description,
#             "profile_picture": profile_picture_url,
#             "cover_image": cover_image_url,
#             "is_verified": owner.is_verified,
#             "created_at": salon.created_at,
#         },
#         "viewer": {
#             "is_following": is_following,
#             "notifications_enabled": notifications_enabled,
#             "is_blocked": is_blocked,
#         },
#         "metrics": {
#             "followers_count": followers_count,
#             "posts_count": posts_count,
#             "rating": round(float(rating_avg), 2) if rating_avg else 0.0,
#             "reviews_count": reviews_count,
#         },
#         "availability": {
#             "is_open_now": is_open_now,
#             "today": today_data,
#             "weekly": weekly,
#         },
#         "contacts": {
#             "phone": contacts_map.get("phone"),
#             "sms": contacts_map.get("sms"),
#             "whatsapp": contacts_map.get("whatsapp"),
#             "email": contacts_map.get("email"),
#             "location": location,
#         },
#         "media": {
#             "gallery": gallery_items,
#         },
#         "actions": {
#             "can_follow": not is_blocked,
#             "can_unfollow": is_following and not is_blocked,
#             "can_contact": not is_blocked,
#             "can_share": True,
#             "can_report": not is_blocked,
#             "can_block": True,
#         },
#         "services": {
#             "categories": list(services_by_category.values())
#         }

#     }


from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from core.r2_config import BASE_URL
from core.enumeration import BookingStatus, ImageDirectories, ServiceCreatedStatus
from models.auth.user import User
from models.auth.profile_picture import ProfilePicture
from models.posts.posts import Post
from models.booking.booking import Booking, ServiceReview
from models.saved import SavedSalon
from models.profile.salon import (
    Salon,
    SalonFollower,
    SalonBlock,
    SalonReport,
    SalonServicePrice,
    SalonStylist,
    StylistService,
)


PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"
COVER_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.SALON_COVER_DIR.value}"
SALON_GALLERY_BASE = f"{BASE_URL}/{ImageDirectories.SALON_GALLERY_DIR.value}"


def _salon_verification_state(
    *,
    db: Session,
    salon: Salon,
    owner: User,
    contacts_map: dict,
    location: dict | None,
    service_prices: list[SalonServicePrice],
    rating_avg,
    reviews_count: int,
    posts_count: int,
) -> dict:
    active_services = [
        sp for sp in service_prices if sp.status == ServiceCreatedStatus.ACTIVE
    ]
    open_days = [
        wh for wh in salon.working_hours if wh.is_open and wh.open_time and wh.close_time
    ]
    verified_contacts = [
        c for c in salon.contacts if c.is_verified and c.type in {"phone", "email", "whatsapp"}
    ]
    completed_bookings_count = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.salon_id == salon.id,
            Booking.status == BookingStatus.COMPLETED,
        )
        .scalar()
        or 0
    )
    reports_count = (
        db.query(func.count(SalonReport.id))
        .filter(SalonReport.salon_id == salon.id)
        .scalar()
        or 0
    )
    salon_created_at = salon.created_at
    if salon_created_at.tzinfo is None:
        salon_created_at = salon_created_at.replace(tzinfo=timezone.utc)
    account_age_days = (datetime.now(timezone.utc) - salon_created_at).days

    criteria = [
        (
            bool(owner.is_verified),
            "Owner email is verified",
            "Verify the salon owner email",
        ),
        (
            bool(salon.title and salon.description and salon.slogan),
            "Salon profile is complete",
            "Complete salon name, slogan, and description",
        ),
        (
            account_age_days >= 30,
            "Salon account has been active for 30+ days",
            "Keep the salon active for at least 30 days",
        ),
        (
            bool(salon.display_ads and len(salon.galleries) >= 3),
            "Salon has real cover and 3+ gallery photos",
            "Add a cover photo and at least 3 gallery photos",
        ),
        (
            bool(location and location.get("lat") is not None and location.get("lng") is not None),
            "Salon location is set",
            "Add a verified salon location",
        ),
        (
            len(verified_contacts) >= 2,
            "At least two contact methods are verified",
            "Verify at least two contact methods",
        ),
        (
            len(active_services) >= 3,
            "Three or more active services are published",
            "Publish at least 3 active services with pricing",
        ),
        (
            len(open_days) >= 5,
            "Working hours cover 5+ open days",
            "Set working hours for at least 5 days",
        ),
        (
            posts_count >= 3,
            "Salon has posted 3+ examples of work",
            "Publish at least 3 salon posts",
        ),
        (
            completed_bookings_count >= 10,
            "Salon has completed 10+ bookings",
            "Complete at least 10 bookings",
        ),
        (
            reviews_count >= 10 and float(rating_avg or 0) >= 4.5,
            "Customer trust signals are excellent",
            "Earn at least 10 reviews with a 4.5+ rating",
        ),
        (
            reports_count == 0,
            "Salon has a clean report history",
            "Resolve trust and safety reports before verification",
        ),
    ]

    earned = [ok for ok, _, _ in criteria if ok]
    reasons = [reason for ok, reason, _ in criteria if ok]
    missing = [missing for ok, _, missing in criteria if not ok]
    is_verified = len(earned) == len(criteria)

    return {
        "is_verified": is_verified,
        "verification_status": "verified" if is_verified else "earning",
        "verification_label": "Verified Salon" if is_verified else "Earning verification",
        "verification_reasons": reasons,
        "verification_missing": missing,
    }


def _salon_premium_state(*, salon: Salon) -> dict:
    now = datetime.now(timezone.utc)
    sponsored = salon.sponsored
    start_at = sponsored.start_at if sponsored else None
    end_at = sponsored.end_at if sponsored else None
    if start_at and start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    if end_at and end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=timezone.utc)
    is_premium = bool(
        sponsored
        and sponsored.is_active
        and start_at
        and end_at
        and start_at <= now
        and end_at >= now
    )
    plan = sponsored.plan_type if is_premium else None
    return {
        "is_premium_member": is_premium,
        "premium_plan": plan,
        "premium_label": "Premium Member" if is_premium else None,
    }


async def view_salon_profile(
    *,
    db: Session,
    salon_id: str,
    viewer_id: str | None,
):
    salon: Salon | None = (
        db.query(Salon)
        .options(
            joinedload(Salon.user),
            joinedload(Salon.contacts),
            joinedload(Salon.working_hours),
            joinedload(Salon.location),
            joinedload(Salon.galleries),
        )
        .filter(Salon.id == salon_id)
        .first()
    )

    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    owner: User = salon.user

    is_following = False
    notifications_enabled = False
    is_blocked = False
    is_owner = bool(viewer_id) and viewer_id == salon.user_id
    is_saved = False

    if viewer_id and not is_owner:
        follow = (
            db.query(SalonFollower)
            .filter(
                SalonFollower.salon_id == salon.id,
                SalonFollower.user_id == viewer_id,
            )
            .first()
        )

        if follow:
            is_following = True
            notifications_enabled = follow.notifications_enabled

        is_blocked = (
            db.query(SalonBlock)
            .filter(
                SalonBlock.salon_id == salon.id,
                SalonBlock.user_id == viewer_id,
            )
            .first()
            is not None
        )
        is_saved = (
            db.query(SavedSalon)
            .filter(
                SavedSalon.salon_id == salon.id,
                SavedSalon.user_id == viewer_id,
            )
            .first()
            is not None
        )

    profile_picture = (
        db.query(ProfilePicture)
        .filter(ProfilePicture.user_id == owner.id)
        .first()
    )

    profile_picture_url = (
        f"{PROFILE_IMAGE_BASE}{profile_picture.file_name}"
        if profile_picture
        else None
    )

    cover_image_url = (
        f"{COVER_IMAGE_BASE}{salon.display_ads}"
        if salon.display_ads
        else None
    )

    gallery_items = []
    for index, g in enumerate(
        sorted(salon.galleries, key=lambda x: x.created_at), start=1
    ):
        gallery_items.append(
            {
                "id": g.id,
                "image_url": f"{SALON_GALLERY_BASE}{g.file_name}",
                "order": index,
            }
        )

    followers_count = (
        db.query(func.count(SalonFollower.id))
        .filter(
            SalonFollower.salon_id == salon.id,
            SalonFollower.user_id != salon.user_id,
        )
        .scalar()
        or 0
    )

    posts_count = (
        db.query(func.count(Post.id))
        .filter(Post.user_id == salon.user_id)
        .scalar()
        or 0
    )

    rating_avg = (
        db.query(func.avg(ServiceReview.rating))
        .filter(ServiceReview.salon_id == salon.id)
        .scalar()
    )

    reviews_count = (
        db.query(func.count(ServiceReview.id))
        .filter(ServiceReview.salon_id == salon.id)
        .scalar()
        or 0
    )

    now = datetime.now(timezone.utc)
    today_weekday = now.weekday()

    today_wh = next(
        (wh for wh in salon.working_hours if wh.day_of_week == today_weekday),
        None,
    )

    is_open_now = False
    today_data = None

    if today_wh and today_wh.is_open and today_wh.open_time and today_wh.close_time:
        current_time = now.time()
        if today_wh.open_time <= current_time <= today_wh.close_time:
            is_open_now = True

        today_data = {
            "day": today_wh.day_of_week,
            "open_time": today_wh.open_time.strftime("%H:%M"),
            "close_time": today_wh.close_time.strftime("%H:%M"),
        }

    weekly = []
    for wh in sorted(salon.working_hours, key=lambda x: x.day_of_week):
        weekly.append(
            {
                "day": wh.day_of_week,
                "is_open": wh.is_open,
                "open": wh.open_time.strftime("%H:%M") if wh.open_time else None,
                "close": wh.close_time.strftime("%H:%M") if wh.close_time else None,
            }
        )

    contacts_map = {c.type: c.value for c in salon.contacts}

    location = None
    if salon.location:
        location = {
            "address": " ".join(
                filter(
                    None,
                    [
                        salon.location.street,
                        salon.location.city,
                        salon.location.region,
                        salon.location.country,
                    ],
                )
            ),
            "lat": salon.location.latitude,
            "lng": salon.location.longitude,
        }

    service_prices = (
        db.query(SalonServicePrice)
        .options(
            joinedload(SalonServicePrice.service),
            joinedload(SalonServicePrice.sub_service),
            joinedload(SalonServicePrice.benefits),
            joinedload(SalonServicePrice.products),
            joinedload(SalonServicePrice.bookings),
            joinedload(SalonServicePrice.reviews),
        )
        .filter(SalonServicePrice.salon_id == salon.id)
        .all()
    )

    verification = _salon_verification_state(
        db=db,
        salon=salon,
        owner=owner,
        contacts_map=contacts_map,
        location=location,
        service_prices=service_prices,
        rating_avg=rating_avg,
        reviews_count=reviews_count,
        posts_count=posts_count,
    )

    stylist_map = {}

    stylist_services = (
        db.query(StylistService)
        .join(SalonStylist)
        .join(User)
        .options(
            joinedload(StylistService.stylist).joinedload(SalonStylist.user)
        )
        .filter(SalonStylist.salon_id == salon.id)
        .all()
    )

    for ss in stylist_services:
        stylist_map.setdefault(ss.salon_service_price_id, []).append(
            {
                "id": ss.stylist.id,
                "name": ss.stylist.user.name,
                "avatar": (
                    f"{PROFILE_IMAGE_BASE}{ss.stylist.user.profile_picture.file_name}"
                    if ss.stylist.user.profile_picture
                    else None
                ),
            }
        )

    services_by_category = {}

    for sp in service_prices:
        if not sp.service:
            continue

        cat_id = sp.service.id
        cat_name = sp.service.name

        services_by_category.setdefault(cat_id, {
            "category_id": cat_id,
            "category_name": cat_name,
            "services": [],
        })

        services_by_category[cat_id]["services"].append(
            {
                "id": sp.id,
                "category_id": cat_id,
                "category_name": cat_name,
                "sub_service_id": sp.sub_service.id if sp.sub_service else None,
                "name": sp.sub_service.name if sp.sub_service else cat_name,
                "image": None,
                "price_min": sp.price_min,
                "price_max": sp.price_max,
                "currency": sp.currency,
                "duration_minutes": sp.duration_minutes,
                "stylists": stylist_map.get(sp.id, []),
            }
        )

    return {
        "salon": {
            "id": salon.id,
            "username": owner.username,
            "name": salon.title,
            "slogan": salon.slogan,
            "description": salon.description,
            "profile_picture": profile_picture_url,
            "cover_image": cover_image_url,
            **verification,
            **_salon_premium_state(salon=salon),
            "created_at": salon.created_at,
        },
        "viewer": {
            "is_following": is_following,
            "notifications_enabled": notifications_enabled,
            "is_blocked": is_blocked,
            "is_owner": is_owner,
            "is_saved": is_saved,
        },
        "metrics": {
            "followers_count": followers_count,
            "posts_count": posts_count,
            "rating": round(float(rating_avg), 2) if rating_avg else 0.0,
            "reviews_count": reviews_count,
        },
        "availability": {
            "is_open_now": is_open_now,
            "today": today_data,
            "weekly": weekly,
        },
        "contacts": {
            "phone": contacts_map.get("phone"),
            "sms": contacts_map.get("sms"),
            "whatsapp": contacts_map.get("whatsapp"),
            "email": contacts_map.get("email"),
            "location": location,
        },
        "media": {
            "gallery": gallery_items,
        },
        "actions": {
            "can_follow": not is_owner and not is_following and not is_blocked,
            "can_unfollow": not is_owner and is_following and not is_blocked,
            "can_contact": not is_blocked,
            "can_share": True,
            "can_report": not is_owner and not is_blocked,
            "can_block": not is_owner,
        },
        "services": {
            "categories": list(services_by_category.values())
        }
    }
