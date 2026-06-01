
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from core.enumeration import (
    BookingStatus,
    PostCollectionType,
    PostStatus,
    PostVisibility,
    ImageURL,
)

from models.booking.booking import Booking, ServiceReview
from models.saved import SavedSalon, SavedService
from models.search.search import SearchHistory
from models.services.service import UserSelectServices
from models.posts.posts import (
    Post,
    PostBoorkmark,
    PostComment,
    PostLike,
    PostReaction,
    PostShare,
    PostSettings,
)

from models.auth.user import User
from models.profile.salon import SalonFollower, Salon, SalonLocation, SalonServiceBenefit, SalonServicePrice, SalonServiceProduct, SalonStylist, SponsoredSalon, StylistService
from pydantic_schemas.posts.single_post import BookingState, EngagementState, OtherPostsSection, PostPreview, PriceRange, ReviewSection, ServiceProduct, ServiceSection, SimilarSection, SinglePostResponse, SponsoredSalonSection, StylistSection
from service.trending.logic import apply_trending_logic
from service.posts.repost import can_share_post
from service.account.enforcement import customer_recommendation_controls

from core.r2_config import BASE_URL 
from core.enumeration import (
    BookingStatus,
    PostCollectionType,
    PostStatus,
    PostVisibility,
    ImageDirectories,
)


# ------------------------------------------------------------------
# URLs
# ------------------------------------------------------------------
# IMAGE_URL = ImageURL.POSTS_URL.value
# PROFILE_URL = ImageURL.PROFILE_URL.value

POST_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.POST_DIR.value}"
PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"
SALON_COVER_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.SALON_COVER_DIR.value}"


# ------------------------------------------------------------------
# Baby feed model
# ------------------------------------------------------------------
FEED_RANKING_MODEL_VERSION = "baby-linear-v1"
FEED_RANKING_WEIGHTS = {
    "followed_salon": 30.0,
    "saved_salon": 22.0,
    "saved_sub_service": 18.0,
    "booked_salon": 18.0,
    "booked_sub_service": 16.0,
    "selected_service": 14.0,
    "recent_search_match": 8.0,
    "engagement": 20.0,
    "has_media": 3.0,
}


def _baby_feed_score(features: Dict[str, float]) -> float:
    return sum(
        FEED_RANKING_WEIGHTS[name] * float(features.get(name, 0.0))
        for name in FEED_RANKING_WEIGHTS
    )


# ------------------------------------------------------------------
# Cursor helper
# ------------------------------------------------------------------
def _parse_cursor(cursor: Optional[str]) -> Optional[datetime]:
    if not cursor:
        return None
    try:
        return datetime.fromisoformat(cursor)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor format",
        )

# --------------------------------------------------
# URL builders
# --------------------------------------------------
def build_profile_url(file_name: Optional[str]) -> Optional[str]:
    if not file_name:
        return None
    return f"{PROFILE_IMAGE_BASE}{file_name}"


def build_post_media_url(file_name: Optional[str]) -> Optional[str]:
    if not file_name:
        return None
    return f"{POST_IMAGE_BASE}{file_name}"


def build_salon_cover_url(file_name: Optional[str]) -> Optional[str]:
    if not file_name:
        return None
    return f"{SALON_COVER_IMAGE_BASE}{file_name}"


def _rank_explore_posts(posts: List[Post], user_id: str, db: Session) -> List[Post]:
    post_ids = [post.id for post in posts]
    salon_ids = [post.user.salon.id for post in posts if post.user and post.user.salon]
    sub_service_ids = [post.sub_service_id for post in posts if post.sub_service_id]

    controls = customer_recommendation_controls(db, user_id)

    followed_salon_ids = set()
    if controls.use_following and salon_ids:
        followed_salon_ids = {
            row[0]
            for row in db.query(SalonFollower.salon_id)
            .filter(
                SalonFollower.user_id == user_id,
                SalonFollower.salon_id.in_(salon_ids),
            )
            .all()
        }

    saved_salon_ids = set()
    saved_sub_service_ids = set()
    if controls.use_saved:
        if salon_ids:
            saved_salon_ids = {
                row[0]
                for row in db.query(SavedSalon.salon_id)
                .filter(
                    SavedSalon.user_id == user_id,
                    SavedSalon.salon_id.in_(salon_ids),
                )
                .all()
            }
        if sub_service_ids:
            saved_sub_service_ids = {
                row[0]
                for row in db.query(SavedService.sub_service_id)
                .filter(
                    SavedService.user_id == user_id,
                    SavedService.sub_service_id.in_(sub_service_ids),
                )
                .all()
                if row[0]
            }

    booked_salon_ids = set()
    booked_sub_service_ids = set()
    if controls.use_bookings:
        if salon_ids:
            booked_salon_ids = {
                row[0]
                for row in db.query(Booking.salon_id)
                .filter(
                    Booking.customer_id == user_id,
                    Booking.salon_id.in_(salon_ids),
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
                )
                .all()
            }
        if sub_service_ids:
            booked_sub_service_ids = {
                row[0]
                for row in db.query(SalonServicePrice.sub_service_id)
                .join(Booking, Booking.salon_service_price_id == SalonServicePrice.id)
                .filter(
                    Booking.customer_id == user_id,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
                    SalonServicePrice.sub_service_id.in_(sub_service_ids),
                )
                .all()
                if row[0]
            }

    selected_service_ids: set[str] = set()
    selected = (
        db.query(UserSelectServices.services)
        .filter(UserSelectServices.user_id == user_id)
        .first()
    )
    if selected and selected[0]:
        selected_service_ids = set(selected[0])

    searched_entity_ids = {
        row[0]
        for row in db.query(SearchHistory.entity_id)
        .filter(
            SearchHistory.user_id == user_id,
            SearchHistory.entity_id.isnot(None),
            SearchHistory.entity.in_(["salon", "service"]),
        )
        .order_by(SearchHistory.created_at.desc())
        .limit(50)
        .all()
        if row[0]
    }

    engagement_rows = (
        db.query(
            Post.id,
            func.count(func.distinct(PostLike.id)).label("likes"),
            func.count(func.distinct(PostComment.id)).label("comments"),
            func.count(func.distinct(PostShare.id)).label("shares"),
        )
        .outerjoin(PostLike, and_(PostLike.post_id == Post.id, PostLike.liked.is_(True)))
        .outerjoin(PostComment, PostComment.post_id == Post.id)
        .outerjoin(PostShare, PostShare.post_id == Post.id)
        .filter(Post.id.in_(post_ids))
        .group_by(Post.id)
        .all()
    )
    engagement = {
        row.id: int(row.likes or 0) + int(row.comments or 0) * 2 + int(row.shares or 0) * 3
        for row in engagement_rows
    }

    def features_for(post: Post) -> Dict[str, float]:
        salon = post.user.salon if post.user else None
        salon_id = salon.id if salon else None
        sub_service_id = post.sub_service_id
        engagement_score = min(float(engagement.get(post.id, 0)), 100.0) / 100.0

        return {
            "followed_salon": 1.0 if salon_id and salon_id in followed_salon_ids else 0.0,
            "saved_salon": 1.0 if salon_id and salon_id in saved_salon_ids else 0.0,
            "saved_sub_service": 1.0 if sub_service_id and sub_service_id in saved_sub_service_ids else 0.0,
            "booked_salon": 1.0 if salon_id and salon_id in booked_salon_ids else 0.0,
            "booked_sub_service": 1.0 if sub_service_id and sub_service_id in booked_sub_service_ids else 0.0,
            "selected_service": 1.0 if sub_service_id and sub_service_id in selected_service_ids else 0.0,
            "recent_search_match": 1.0
            if (salon_id and salon_id in searched_entity_ids)
            or (sub_service_id and sub_service_id in searched_entity_ids)
            else 0.0,
            "engagement": engagement_score,
            "has_media": 1.0 if post.media_items else 0.0,
        }

    return sorted(
        posts,
        key=lambda post: (_baby_feed_score(features_for(post)), post.created_at),
        reverse=True,
    )


# ==============================================================
# TIMELINE POSTS (feed / explore / trending / saved)
# ==============================================================
async def get_posts_(
    user_id: str,
    option: PostCollectionType,
    db: Session,
    cursor: Optional[str],
    limit: int,
) -> Dict[str, Any]:

    cursor_dt = _parse_cursor(cursor)

    # subquery: user IDs of salons the viewer follows
    followed_salon_user_ids = (
        select(Salon.user_id)
        .where(
            Salon.id.in_(
                select(SalonFollower.salon_id)
                .where(SalonFollower.user_id == user_id)
            )
        )
    )

    query = (
        db.query(Post)
        .outerjoin(PostSettings, PostSettings.post_id == Post.id)
        .options(
            joinedload(Post.user)
            .joinedload(User.profile_picture),

            joinedload(Post.user)
            .joinedload(User.salon)
            .joinedload(Salon.location),

            joinedload(Post.media_items),
        )
        .filter(Post.status == PostStatus.PUBLISHED)
    )

    if option == PostCollectionType.feed:
        # own posts: any visibility
        # followed salon posts: PUBLIC or FRIENDS
        query = query.filter(
            or_(
                Post.user_id == user_id,
                and_(
                    Post.user_id.in_(followed_salon_user_ids),
                    or_(
                        PostSettings.visibility == PostVisibility.PUBLIC,
                        PostSettings.visibility == PostVisibility.FRIENDS,
                        PostSettings.id.is_(None),
                    ),
                ),
            )
        )

    elif option == PostCollectionType.trending:
        query = query.filter(
            or_(PostSettings.visibility == PostVisibility.PUBLIC, PostSettings.id.is_(None))
        )
        query = apply_trending_logic(
            base_query=query,
            db=db,
            user_id=user_id,
            limit=limit,
        )

    elif option == PostCollectionType.saved:
        saved_posts = (
            select(PostBoorkmark.post_id)
            .where(PostBoorkmark.user_id == user_id)
        )
        query = query.filter(Post.id.in_(saved_posts))

    elif option == PostCollectionType.explore:
        query = query.filter(
            or_(PostSettings.visibility == PostVisibility.PUBLIC, PostSettings.id.is_(None))
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post collection type",
        )

    if cursor_dt:
        query = query.filter(Post.created_at < cursor_dt)

    posts = query.order_by(Post.created_at.desc()).limit(limit).all()

    if option == PostCollectionType.explore and posts:
        posts = _rank_explore_posts(posts, user_id, db)

    return _build_posts_response(posts, user_id, db)


# ==============================================================
# PROFILE POSTS (OWNER / VISITOR)
# ==============================================================
async def get_profile_posts_(
    viewer_user_id: str,
    profile_user_id: str,
    db: Session,
    cursor: Optional[str],
    limit: int,
) -> Dict[str, Any]:

    cursor_dt = _parse_cursor(cursor)
    
    salon = db.query(Salon).filter(Salon.id == profile_user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    profile_user_id = salon.user_id
    
    query = (
        db.query(Post)
        .outerjoin(PostSettings, PostSettings.post_id == Post.id)
        .options(
            joinedload(Post.user)
            .joinedload(User.profile_picture),

            joinedload(Post.user)
            .joinedload(User.salon)
            .joinedload(Salon.location),

            joinedload(Post.media_items),
        )
        .filter(
            Post.user_id == profile_user_id,
            Post.status == PostStatus.PUBLISHED.name,
        )
    )

    if viewer_user_id != profile_user_id:
        query = query.filter(
            or_(
                PostSettings.visibility == PostVisibility.PUBLIC.name,
                PostSettings.id.is_(None),
            )
        )

    if cursor_dt:
        query = query.filter(Post.created_at < cursor_dt)

    posts = (
        query.order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

    return _build_posts_response(posts, viewer_user_id, db)


# ==============================================================
# SHARED RESPONSE BUILDER
# ==============================================================
def _build_posts_response(
    posts: List[Post],
    viewer_user_id: str,
    db: Session,
) -> Dict[str, Any]:

    if not posts:
        return {"items": [], "next_cursor": None}

    post_ids = [p.id for p in posts]

    likes_map = dict(
        db.query(PostLike.post_id, func.count(PostLike.id))
        .filter(PostLike.post_id.in_(post_ids), PostLike.liked.is_(True))
        .group_by(PostLike.post_id)
        .all()
    )

    comments_map = dict(
        db.query(PostComment.post_id, func.count(PostComment.id))
        .filter(PostComment.post_id.in_(post_ids))
        .group_by(PostComment.post_id)
        .all()
    )

    shares_map = dict(
        db.query(PostShare.post_id, func.count(PostShare.id))
        .filter(PostShare.post_id.in_(post_ids))
        .group_by(PostShare.post_id)
        .all()
    )

    liked_set = {
        r[0]
        for r in db.query(PostLike.post_id)
        .filter(
            PostLike.post_id.in_(post_ids),
            PostLike.user_id == viewer_user_id,
            PostLike.liked.is_(True),
        )
        .all()
    }

    saved_set = {
        r[0]
        for r in db.query(PostBoorkmark.post_id)
        .filter(
            PostBoorkmark.post_id.in_(post_ids),
            PostBoorkmark.user_id == viewer_user_id,
        )
        .all()
    }

    items = []

    for post in posts:
        author = post.user
        salon = author.salon if author else None
        location = salon.location if salon else None

        items.append(
            {
                "id": post.id,
                "post_type": post.post_type or "service",
                "author": {
                    "user_id": author.id,
                    "username": author.username,
                    "is_verified": author.is_verified,
                    # "profile_picture": (
                    #     f"{PROFILE_URL}{author.profile_picture.file_name}"
                    #     if author.profile_picture
                    #     else None
                    # ),
                    "profile_picture": (
                        build_profile_url(author.profile_picture.file_name)
                        if author.profile_picture
                        else None
                    ),
                    "salon": {
                        "id": salon.id if salon else None,
                        "title": salon.title if salon else None,
                        "address": {
                            "city": location.city,
                            "country": location.country,
                            "latitude": location.latitude,
                            "longitude": location.longitude,
                        } if location
                        else None,
                    } if salon else None,
                },
                
                "caption": post.caption_text,
                "media": [
                    {
                        # "url": f"{IMAGE_URL}{m.media_url}",
                        "url": build_post_media_url(m.media_url),
                        "type": m.media_type.name,
                        "aspect_ratio": m.aspect_ratio,
                    }
                    for m in post.media_items
                ],
                "service": post.sub_service.id if post.sub_service else None,
                "stats": { 
                    "likes": likes_map.get(post.id, 0), 
                    "comments": comments_map.get(post.id, 0), 
                    "shares": shares_map.get(post.id, 0), 
                },
                "viewer_state": {
                    "is_liked": post.id in liked_set,
                    "is_saved": post.id in saved_set,
                    "is_my_post": post.user_id == viewer_user_id,
                },
                "created_at": post.created_at,
            }
        )

    return {
        "items": items,
        "next_cursor": posts[-1].created_at.isoformat(),
    }


# ==============================================================
# SINGLE POST
# ==============================================================
async def get_post__(
    user_id: str,
    post_id: str,
    db: Session,
) -> Dict[str, Any]:

    post = (
        db.query(Post)
        .options(
            joinedload(Post.user)
            .joinedload(User.profile_picture),

            joinedload(Post.user)
            .joinedload(User.salon)
            .joinedload(Salon.location),

            joinedload(Post.media_items),
        )
        .join(PostSettings, PostSettings.post_id == Post.id)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.status != PostStatus.PUBLISHED:
        if post.user_id != user_id:
            raise HTTPException(status_code=403, detail="Post not available")

    settings = post.settings
    if settings and post.user_id != user_id:
        if settings.visibility == PostVisibility.PRIVATE:
            raise HTTPException(status_code=403, detail="Permission denied")
        elif settings.visibility == PostVisibility.FRIENDS:
            salon = db.query(Salon).filter(Salon.user_id == post.user_id).first()
            is_follower = (
                salon and
                db.query(SalonFollower)
                .filter(
                    SalonFollower.salon_id == salon.id,
                    SalonFollower.user_id == user_id,
                )
                .first() is not None
            )
            if not is_follower:
                raise HTTPException(status_code=403, detail="Permission denied")

    likes = (
        db.query(func.count(PostLike.id))
        .filter(PostLike.post_id == post_id, PostLike.liked.is_(True))
        .scalar()
        or 0
    )

    comments = (
        db.query(func.count(PostComment.id))
        .filter(PostComment.post_id == post_id)
        .scalar()
        or 0
    )

    shares = (
        db.query(func.count(PostShare.id))
        .filter(PostShare.post_id == post_id)
        .scalar()
        or 0
    )
    reactions = dict(
        db.query(PostReaction.reaction, func.count(PostReaction.id))
        .filter(PostReaction.post_id == post_id)
        .group_by(PostReaction.reaction)
        .all()
    )
    my_reaction = (
        db.query(PostReaction.reaction)
        .filter(PostReaction.post_id == post_id, PostReaction.user_id == user_id)
        .scalar()
    )

    is_liked = (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id,
            PostLike.liked.is_(True),
        )
        .first()
        is not None
    )

    is_saved = (
        db.query(PostBoorkmark)
        .filter(
            PostBoorkmark.post_id == post_id,
            PostBoorkmark.user_id == user_id,
        )
        .first()
        is not None
    )

    author = post.user
    salon = author.salon if author else None
    location = salon.location if salon else None

    return {
        "id": post.id,
        "post_type": post.post_type or "service",
        "author": {
            "user_id": author.id,
            "username": author.username,
            "is_verified": author.is_verified,
            # "profile_picture": (
            #     f"{PROFILE_URL}{author.profile_picture.file_name}"
            #     if author.profile_picture
            #     else None
            # ),
            "profile_picture": (
                build_profile_url(author.profile_picture.file_name)
                if author.profile_picture
                else None
            ),
            "salon": {
                "id": salon.id if salon else None,
                "title": salon.title if salon else None,
                "address": {
                    "city": location.city,
                    "country": location.country,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                } if location
                else None,
            } if salon else None,
        },
        
        "caption": post.caption_text,
        "media": [
            {
                # "url": f"{IMAGE_URL}{m.media_url}",
                "url": build_post_media_url(m.media_url),
                "type": m.media_type.name,
                "aspect_ratio": m.aspect_ratio,
            }
            for m in post.media_items
        ],
        "service": post.sub_service.id if post.sub_service else None,
        "stats": { 
            "likes": likes or 0, 
            "comments": comments or 0, 
            "shares": shares or 0, 
        },
        "reactions": reactions,
        "viewer_state": {
            "is_liked": is_liked,
            "is_saved": is_saved,
            "is_my_post": post.user_id == user_id,
            "reaction": my_reaction,
        },
        "created_at": post.created_at,
    }
    
    

def _map_post_to_post_response_schema(raw: Dict[str, Any]) -> Dict[str, Any]:
    author = raw["author"]
    salon = author.get("salon")
    address = salon.get("address") if salon else None

    return {
        "id": raw["id"],
        "post_type": raw.get("post_type", "service"),

        "author": {
            "id": author["user_id"],
            "salon_id": salon["id"] if salon else None,
            "salon_name": salon["title"] if salon else "",
            "username": author["username"],
            "display_picture": author.get("profile_picture"),
            "is_verified": author.get("is_verified", False),
            "location": address,
        },

        "description": raw.get("caption"),

        "images": [
            {
                "url": m["url"],
                "type": m["type"].lower(),
                "aspect_ratio": m.get("aspect_ratio"),
            }
            for m in raw.get("media", [])
        ],

        "service": {
            "category": "",        # placeholder for now
            "price": 0.0,
            "duration_minutes": 0,
            "assigned_servicer": None,
        },

        "stats": raw["stats"],
        "reactions": raw.get("reactions", {}),

        "viewer_state": raw["viewer_state"],

        "created_at": raw["created_at"],
    }
 
 
# Build Service Context
def _build_service_context(
    db: Session,
    post: Post,
) -> ServiceSection:

    # Get salon from post owner (correct model)
    salon = post.user.salon if post.user else None

    if not salon or not post.sub_service_id:
        return ServiceSection(
            id="",
            subname="",
            name="",
            price=PriceRange(min=None, max=None, currency="TZS"),
            duration_minutes=None,
            benefits=[],
            products=[],
        )

    #  Get salon-specific service pricing
    service_price = (
        db.query(SalonServicePrice)
        .options(
            joinedload(SalonServicePrice.service),
            joinedload(SalonServicePrice.sub_service),
        )
        .filter(
            SalonServicePrice.salon_id == salon.id,
            SalonServicePrice.sub_service_id == post.sub_service_id,
        )
        .first()
    )

    if not service_price:
        return ServiceSection(
            id="",
            subname="",
            name="",
            price=PriceRange(min=None, max=None, currency="TZS"),
            duration_minutes=None,
            benefits=[],
            products=[],
        )

    # Benefits
    benefits = (
        db.query(SalonServiceBenefit)
        .filter(
            SalonServiceBenefit.salon_service_price_id == service_price.id
        )
        .order_by(SalonServiceBenefit.created_at.asc())
        .all()
    )

    # Products / Tools
    products = (
        db.query(SalonServiceProduct)
        .filter(
            SalonServiceProduct.salon_service_price_id == service_price.id
        )
        .order_by(SalonServiceProduct.created_at.asc())
        .all()
    )

    return ServiceSection(
        id=service_price.id,
        subname=(
            service_price.sub_service.name
            if service_price.sub_service
            else service_price.service.name
            if service_price.service
            else ""
        ),
        name=service_price.service.name if service_price.service else "",
        price=PriceRange(
            min=service_price.price_min,
            max=service_price.price_max,
            currency=service_price.currency or "TZS",
        ),
        duration_minutes=service_price.duration_minutes,
        benefits=[b.benefit for b in benefits],
        products=[
            ServiceProduct(
                name=p.product_name,
                brand=p.brand,
            )
            for p in products
        ],
    )


# Booking Section
def _build_booking_state(
    db: Session,
    current_user: str,   
    post: Post,
    service_price_id: Optional[str],
) -> BookingState:

    if not service_price_id:
        return BookingState(can_book=True, has_booked_before=False, can_review=False)

    if post.user_id == current_user.user_id:
        return BookingState(can_book=False, has_booked_before=False, can_review=False)

    bookings = (
        db.query(Booking)
        .filter(
            Booking.customer_id == current_user.user_id,
            Booking.salon_service_price_id == service_price_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
        )
        .all()
    )

    has_booked_before = bool(bookings)

    completed_booking_ids = [b.id for b in bookings if b.status == BookingStatus.COMPLETED]

    if not completed_booking_ids:
        return BookingState(can_book=True, has_booked_before=has_booked_before, can_review=False)

    reviewed_booking_ids = {
        r[0]
        for r in db.query(ServiceReview.booking_id)
        .filter(ServiceReview.booking_id.in_(completed_booking_ids))
        .all()
    }

    can_review = any(bid not in reviewed_booking_ids for bid in completed_booking_ids)

    return BookingState(
        can_book=True,
        has_booked_before=has_booked_before,
        can_review=can_review,
    )



# Review Section
def _build_review_section(
    db: Session,
    salon_service_price_id: Optional[str],
) -> ReviewSection:
    """
    Build reviews section for a service.
    """

    if not salon_service_price_id:
        return ReviewSection(
            count=0,
            average=None,
            items=[],
        )

    reviews = (
        db.query(ServiceReview)
        .options(
            joinedload(ServiceReview.user)
            .joinedload(User.profile_picture)
        )
        .filter(
            ServiceReview.salon_service_price_id == salon_service_price_id
        )
        .order_by(ServiceReview.created_at.desc())
        .all()
    )

    if not reviews:
        return ReviewSection(
            count=0,
            average=None,
            items=[],
        )

    avg_rating = (
        db.query(func.avg(ServiceReview.rating))
        .filter(
            ServiceReview.salon_service_price_id == salon_service_price_id
        )
        .scalar()
    )

    return ReviewSection(
        count=len(reviews),
        average=round(float(avg_rating), 1) if avg_rating else None,
        items=[
            {
                "id": r.id,
                "user_name": r.user.username,
                # "user_avatar": (
                #     f"{PROFILE_URL}{r.user.profile_picture.file_name}"
                #     if r.user.profile_picture
                #     else None
                # ),
                "user_avatar": (
                    build_profile_url(r.user.profile_picture.file_name)
                    if r.user.profile_picture
                    else None
                ),
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ],
    )



# Similar Result
def _post_to_preview(post: Post, salon: Optional[Salon] = None) -> PostPreview:
    media = post.media_items[0] if post.media_items else None
    return PostPreview(
        id=post.id,
        cover_image=build_post_media_url(media.media_url) if media else "",
        salon_name=salon.title if salon else None,
        salon_id=salon.id if salon else None,
    )


def _build_similar_section(
    db: Session,
    viewer_user_id: str,
    post: Post,
    limit: int = 8,
) -> SimilarSection:
    """
    Posts from salons the viewer FOLLOWS that offer the same sub-service.
    Deduplicated so each salon contributes at most one post (most recent).
    Excludes the current post's salon.
    """

    if not post.sub_service_id:
        return SimilarSection(items=[])

    current_salon = db.query(Salon).filter(Salon.user_id == post.user_id).first()

    followed_salon_ids = (
        select(SalonFollower.salon_id)
        .where(SalonFollower.user_id == viewer_user_id)
    )

    # Salon user_ids the viewer follows (post author ids)
    followed_salon_user_ids = (
        select(Salon.user_id)
        .where(Salon.id.in_(followed_salon_ids))
    )

    candidates = (
        db.query(Post, Salon)
        .join(Salon, Salon.user_id == Post.user_id)
        .options(joinedload(Post.media_items))
        .filter(
            Post.status == PostStatus.PUBLISHED.name,
            Post.id != post.id,
            Post.sub_service_id == post.sub_service_id,
            Post.user_id.in_(followed_salon_user_ids),
            Salon.id != (current_salon.id if current_salon else ""),
        )
        .order_by(Post.created_at.desc())
        .limit(limit * 4)
        .all()
    )

    seen_salons: set[str] = set()
    items: List[PostPreview] = []
    for p, salon in candidates:
        if salon.id in seen_salons:
            continue
        seen_salons.add(salon.id)
        items.append(_post_to_preview(p, salon=salon))
        if len(items) >= limit:
            break

    return SimilarSection(items=items)




# Other Posts
def _resolve_viewer_location(
    db: Session,
    viewer_user_id: str,
    viewer_city: Optional[str],
    viewer_country: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Prefer explicit query params; fall back to CustomerProfile."""
    from models.auth.customer_profile import CustomerProfile

    city = viewer_city.strip() if viewer_city else None
    country = viewer_country.strip() if viewer_country else None

    if city and country:
        return city, country

    profile = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.user_id == viewer_user_id)
        .first()
    )
    if profile:
        city = city or profile.city
        country = country or profile.country

    return city, country


def _build_other_posts_section(
    db: Session,
    viewer_user_id: str,
    post: Post,
    exclude_post_ids: set[str],
    cursor: Optional[datetime] = None,
    limit: int = 10,
    viewer_city: Optional[str] = None,
    viewer_country: Optional[str] = None,
) -> OtherPostsSection:
    """
    Continuation feed shown after the similar section.
    Scope (OR):
      - posts from salons the viewer follows
      - posts from salons in the viewer's city/country (for travelers)
    """

    followed_salon_user_ids = (
        select(Salon.user_id)
        .where(
            Salon.id.in_(
                select(SalonFollower.salon_id)
                .where(SalonFollower.user_id == viewer_user_id)
            )
        )
    )

    city, country = _resolve_viewer_location(
        db, viewer_user_id, viewer_city, viewer_country,
    )

    signals = [Post.user_id.in_(followed_salon_user_ids)]

    if city:
        signals.append(SalonLocation.city == city)
    if country:
        signals.append(SalonLocation.country == country)

    query = (
        db.query(Post)
        .join(User, Post.user_id == User.id)
        .join(Salon, Salon.user_id == User.id)
        .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
        .outerjoin(PostSettings, PostSettings.post_id == Post.id)
        .options(
            joinedload(Post.user).joinedload(User.profile_picture),
            joinedload(Post.user).joinedload(User.salon).joinedload(Salon.location),
            joinedload(Post.media_items),
        )
        .filter(
            Post.status == PostStatus.PUBLISHED.name,
            or_(
                PostSettings.visibility == PostVisibility.PUBLIC.name,
                PostSettings.id.is_(None),
            ),
            Post.id.notin_(exclude_post_ids),
            or_(*signals),
        )
    )

    if cursor:
        query = query.filter(Post.created_at < cursor)

    posts = (
        query
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

    if not posts:
        return OtherPostsSection(items=[], next_cursor=None)

    # reuse existing feed builder (CORRECT)
    raw_response = _build_posts_response(
        posts=posts,
        viewer_user_id=viewer_user_id,
        db=db,
    )

    mapped_items = [
        _map_post_to_post_response_schema(item)
        for item in raw_response["items"]
    ]

    next_cursor = (
        posts[-1].created_at.isoformat()
        if posts
        else None
    )
    
    return OtherPostsSection(
        items=mapped_items,
        next_cursor=next_cursor,
    )


# Stylist
def _build_stylists_section(
    db: Session,
    salon_service_price_id: Optional[str],
) -> List[StylistSection]:

    if not salon_service_price_id:
        return []

    assigned = (
        db.query(StylistService)
        .join(SalonStylist)
        .options(
            joinedload(StylistService.stylist)
            .joinedload(SalonStylist.user)
            .joinedload(User.profile_picture)
        )
        .filter(
            StylistService.salon_service_price_id == salon_service_price_id,
            SalonStylist.is_active.is_(True),
        )
        .order_by(SalonStylist.is_owner.asc(), SalonStylist.created_at.asc())
        .all()
    )

    stylists: List[StylistSection] = []
    seen: set[str] = set()

    for assignment in assigned:
        stylist = assignment.stylist
        user = stylist.user if stylist else None
        if not stylist or not user or stylist.id in seen:
            continue
        seen.add(stylist.id)

        stylists.append(
            StylistSection(
                id=stylist.id,
                name=user.name or user.username,
                avatar=(
                    build_profile_url(user.profile_picture.file_name)
                    if user.profile_picture
                    else None
                ),
                title=stylist.title,
                rating=None,
            )
        )

    return stylists



# Sponsered 
def _build_sponsored_salons_section(
    db: Session,
    limit: int = 5,
) -> List[SponsoredSalonSection]:
    """
    Return currently active sponsored salons.
    """

    now = datetime.utcnow()

    sponsored = (
        db.query(SponsoredSalon)
        .join(Salon)
        .options(
            joinedload(SponsoredSalon.salon)
            .joinedload(Salon.location),
            joinedload(SponsoredSalon.salon)
            .joinedload(Salon.rated),
        )
        .filter(
            SponsoredSalon.is_active.is_(True),
            SponsoredSalon.start_at <= now,
            SponsoredSalon.end_at >= now,
        )
        .limit(limit)
        .all()
    )

    results = []

    for s in sponsored:
        salon = s.salon
        location = salon.location if salon else None

        avg_rating = None
        if salon and salon.rated:
            values = [r.value for r in salon.rated if r.value is not None]
            if values:
                avg_rating = round(sum(values) / len(values), 1)

        results.append(
            SponsoredSalonSection(
                salon_id=salon.id,
                name=salon.title,
                image_url=build_salon_cover_url(salon.display_ads),
                location=(
                    f"{location.city}, {location.country}"
                    if location
                    else None
                ),
                rating=avg_rating,
                price=None,      # optional: marketing price display later
                currency="TZS",
                plan_type=s.plan_type,
            )
        )

    return results



# ==============================================================
# OTHER POSTS (SEPARATE CURSOR ENDPOINT)
# ==============================================================
async def get_other_posts_(
    viewer_user_id: str,
    post_id: str,
    db: Session,
    cursor: Optional[datetime] = None,
    limit: int = 10,
    viewer_city: Optional[str] = None,
    viewer_country: Optional[str] = None,
):
    """
    Paginated continuation feed for a single post view.
    Called after the initial load to load more posts below.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return _build_other_posts_section(
        db=db,
        viewer_user_id=viewer_user_id,
        post=post,
        exclude_post_ids={post_id},
        cursor=cursor,
        limit=limit,
        viewer_city=viewer_city,
        viewer_country=viewer_country,
    )


# ==============================================================
# SINGLE POST VIEW (AGGREGATED)
# Step 1: build post section (reuse get_post__)
# ==============================================================
async def get_single_post_view_(
    current_user: str,
    post_id: str,
    db: Session,
    other_cursor: Optional[datetime] = None,
    viewer_city: Optional[str] = None,
    viewer_country: Optional[str] = None,
) -> SinglePostResponse:
    """
    Single Post View aggregator.

    Step 1:
    - Build core post section using existing get_post__()

    Next steps will fill:
    - service, stylists, reviews, similar, sponsored_salons, other_posts, booking
    """

    post = (
        db.query(Post)
        .options(
            joinedload(Post.user),
        )
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # ----------------------------------------------------------
    # 1) Post section (already includes stats + viewer_state)
    # ----------------------------------------------------------
    raw_post = await get_post__(
        user_id=current_user.user_id,
        post_id=post_id,
        db=db,
    )

    post_data = _map_post_to_post_response_schema(raw_post)


    # ----------------------------------------------------------
    service = _build_service_context(
        db=db,
        post=post,
    )
    
    stylists = _build_stylists_section(
        db=db,
        salon_service_price_id=service.id if service.id else None,
    )



    reviews = _build_review_section(
        db=db,
        salon_service_price_id=service.id if service.id else None,
    )


    similar = _build_similar_section(
        db=db,
        viewer_user_id=current_user.user_id,
        post=post,
    )

    # NOTE:
    # Your PostResponseSchema already contains viewer_state,
    # but SinglePostResponse also exposes engagement/booking at top level.
    # For now we derive from viewer_state if present.
    viewer_state = post_data.get("viewer_state") or {}

    engagement = EngagementState(
        liked=bool(viewer_state.get("is_liked", False)),
        saved=bool(viewer_state.get("is_saved", False)),
        can_comment=not bool(post.settings and post.settings.allow_comments is False),
        can_share=can_share_post(post=post, user_id=current_user.user_id, db=db),
        can_react=not bool(post.settings and post.settings.disable_reactions),
        my_reaction=viewer_state.get("reaction"),
    )

    booking = _build_booking_state(
        db=db,
        current_user=current_user,
        post=post,
        service_price_id=service.id if service.id else None,
    )
    
    exclude_ids = {post.id}
    exclude_ids.update(p.id for p in similar.items)

    sponsored_salons = _build_sponsored_salons_section(db=db)

    other_posts = _build_other_posts_section(
        db=db,
        viewer_user_id=current_user.user_id,
        post=post,
        exclude_post_ids=exclude_ids,
        cursor=other_cursor,
        viewer_city=viewer_city,
        viewer_country=viewer_country,
    )


    # ----------------------------------------------------------
    # 3) Assemble response
    # ----------------------------------------------------------
    return SinglePostResponse(
        post=post_data,                 # PostResponseSchema-compatible dict
        service=service,
        engagement=engagement,
        booking=booking,
        stylists=stylists,
        reviews=reviews,
        similar=similar,
        sponsored_salons=sponsored_salons,
        other_posts=other_posts,
    )
