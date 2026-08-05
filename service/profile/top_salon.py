"""Provides the Top Salon business logic module for profile workflows."""

# from sqlalchemy.orm import Session, joinedload
# from sqlalchemy import func, and_

# from core.enumeration import ImageURL
# from models.auth.user import User
# from models.auth.profile_picture import ProfilePicture
# from models.profile.salon import (
#     Salon,
#     SalonFollower,
#     Rate,
#     SalonLocation,
# )
# from models.posts.posts import Post
# from models.booking.booking import Booking, BookingStatus
# from pydantic_schemas.profile.top_salon import TopSalonCard
# from service.profile.top_salon_ranking import calculate_salon_score

# PROFILE_PIC = ImageURL.PROFILE_URL.value
# COVER_PIC = ImageURL.SALON_COVER_URL.value


# def get_top_salons(db: Session, limit: int = 10):
#     # ───────────────── Aggregates (SUBQUERIES) ─────────────────

#     followers_sq = (
#         db.query(
#             SalonFollower.salon_id.label("salon_id"),
#             func.count(SalonFollower.id).label("followers_count"),
#         )
#         .group_by(SalonFollower.salon_id)
#         .subquery()
#     )

#     posts_sq = (
#         db.query(
#             Post.user_id.label("user_id"),
#             func.count(Post.id).label("posts_count"),
#         )
#         .group_by(Post.user_id)
#         .subquery()
#     )

#     ratings_sq = (
#         db.query(
#             Rate.salon_id,
#             func.coalesce(func.avg(Rate.value), 0).label("avg_rating"),
#         )
#         .group_by(Rate.salon_id)
#         .subquery()
#     )

#     completed_bookings_sq = (
#         db.query(
#             Booking.salon_id,
#             func.count(Booking.id).label("completed_bookings"),
#         )
#         .filter(Booking.status == BookingStatus.COMPLETED)
#         .group_by(Booking.salon_id)
#         .subquery()
#     )

#     # ───────────────── Main query ─────────────────

#     salons = (
#         db.query(
#             Salon,
#             followers_sq.c.followers_count,
#             posts_sq.c.posts_count,
#             ratings_sq.c.avg_rating,
#             completed_bookings_sq.c.completed_bookings,
#             SalonLocation.city,
#         )
#         .outerjoin(followers_sq, followers_sq.c.salon_id == Salon.id)
#         .outerjoin(posts_sq, posts_sq.c.user_id == Salon.user_id)
#         .outerjoin(ratings_sq, ratings_sq.c.salon_id == Salon.id)
#         .outerjoin(completed_bookings_sq, completed_bookings_sq.c.salon_id == Salon.id)
#         .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
#         .options(
#             joinedload(Salon.user).joinedload(User.profile_picture)
#         )
#         .all()
#     )

#     # ───────────────── Ranking ─────────────────

#     ranked = []
#     for (
#         salon,
#         followers_count,
#         posts_count,
#         avg_rating,
#         completed_bookings,
#         city,
#     ) in salons:

#         score = calculate_salon_score(
#             followers=followers_count or 0,
#             posts=posts_count or 0,
#             rating=float(avg_rating or 0),
#             completed_bookings=completed_bookings or 0,
#             profile_completion=salon.profile_completion or 0,
#         )

#         ranked.append((score, salon, city))

#     ranked.sort(key=lambda x: x[0], reverse=True)
#     top_salons = ranked[:limit]

#     # ───────────────── Mapping ─────────────────

#     results = []
#     for _, salon, city in top_salons:
#         logo_url = None
#         if salon.user and salon.user.profile_picture:
#             logo_url = PROFILE_PIC + salon.user.profile_picture.file_name

#         cover_url = (
#             COVER_PIC + salon.display_ads
#             if salon.display_ads
#             else None
#         )

#         results.append(
#             TopSalonCard(
#                 salon_id=salon.id,
#                 name=salon.title,
#                 logo_url=logo_url,
#                 cover_url=cover_url,
#                 city=city,
#                 tagline=salon.slogan,
#             )
#         )

#     return {"results": results}

from sqlalchemy.orm import Session
from sqlalchemy import func

from core.r2_config import BASE_URL
from core.enumeration import ImageDirectories
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.profile.salon import (
    Salon,
    SalonFollower,
    SalonLocation,
)
from models.posts.posts import Post
from models.booking.booking import Booking, BookingStatus, ServiceReview
from pydantic_schemas.pagination import pagination_meta
from pydantic_schemas.profile.top_salon import TopSalonCard

PROFILE_PIC = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"
COVER_PIC = f"{BASE_URL}/{ImageDirectories.SALON_COVER_DIR.value}"


def get_top_salons(
    db: Session,
    limit: int = 10,
    offset: int = 0,
    exclude_user_id: str | None = None,
):
    followers_sq = (
        db.query(
            SalonFollower.salon_id.label("salon_id"),
            func.count(SalonFollower.id).label("followers_count"),
        )
        .group_by(SalonFollower.salon_id)
        .subquery()
    )

    posts_sq = (
        db.query(
            Post.user_id.label("user_id"),
            func.count(Post.id).label("posts_count"),
        )
        .group_by(Post.user_id)
        .subquery()
    )

    ratings_sq = (
        db.query(
            ServiceReview.salon_id,
            func.coalesce(func.avg(ServiceReview.rating), 0).label("avg_rating"),
        )
        .group_by(ServiceReview.salon_id)
        .subquery()
    )

    completed_bookings_sq = (
        db.query(
            Booking.salon_id,
            func.count(Booking.id).label("completed_bookings"),
        )
        .filter(Booking.status == BookingStatus.COMPLETED)
        .group_by(Booking.salon_id)
        .subquery()
    )

    followers = func.coalesce(followers_sq.c.followers_count, 0)
    posts = func.coalesce(posts_sq.c.posts_count, 0)
    rating = func.coalesce(ratings_sq.c.avg_rating, 0)
    completed_bookings = func.coalesce(
        completed_bookings_sq.c.completed_bookings,
        0,
    )
    profile_completion = func.coalesce(Salon.profile_completion, 0)
    score = (
        followers * 0.35
        + posts * 0.15
        + rating * 25
        + completed_bookings * 0.2
        + profile_completion * 15
    ).label("score")

    query = (
        db.query(
            Salon.id,
            Salon.title,
            Salon.slogan,
            Salon.display_ads,
            ProfilePicture.file_name.label("profile_file"),
            SalonLocation.city,
            score,
        )
        .outerjoin(followers_sq, followers_sq.c.salon_id == Salon.id)
        .outerjoin(posts_sq, posts_sq.c.user_id == Salon.user_id)
        .outerjoin(ratings_sq, ratings_sq.c.salon_id == Salon.id)
        .outerjoin(completed_bookings_sq, completed_bookings_sq.c.salon_id == Salon.id)
        .join(User, User.id == Salon.user_id)
        .outerjoin(ProfilePicture, ProfilePicture.user_id == User.id)
        .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
    )
    if exclude_user_id:
        query = query.filter(Salon.user_id != exclude_user_id)

    total = query.count()

    rows = query.order_by(score.desc(), Salon.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for row in rows:
        logo_url = PROFILE_PIC + row.profile_file if row.profile_file else None

        cover_url = (
            COVER_PIC + row.display_ads
            if row.display_ads
            else None
        )

        results.append(
            TopSalonCard(
                salon_id=row.id,
                name=row.title,
                logo_url=logo_url,
                cover_url=cover_url,
                city=row.city,
                tagline=row.slogan,
            )
        )

    return {
        "results": results,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }
