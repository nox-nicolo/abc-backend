
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import func, or_, select
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
from models.posts.posts import (
    Post,
    PostBoorkmark,
    PostComment,
    PostLike,
    PostShare,
    PostSettings,
)

from models.auth.user import User
from models.profile.salon import SalonFollower, Salon, SalonLocation, SalonServiceBenefit, SalonServicePrice, SalonServiceProduct, SponsoredSalon, StylistService
from pydantic_schemas.posts.single_post import BookingState, EngagementState, OtherPostsSection, PostPreview, PriceRange, ReviewSection, ServiceProduct, ServiceSection, SimilarSection, SinglePostResponse, SponsoredSalonSection, StylistSection
from service.trending.logic import apply_trending_logic


# ------------------------------------------------------------------
# URLs
# ------------------------------------------------------------------
IMAGE_URL = ImageURL.POSTS_URL.value
PROFILE_URL = ImageURL.PROFILE_URL.value


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
            Post.status == PostStatus.PUBLISHED.name,
            or_(
                PostSettings.visibility == PostVisibility.PUBLIC.name,
                PostSettings.id.is_(None),
            ),
        )
    )

    if option == PostCollectionType.feed:
        followed_users = (
            select(SalonFollower.following_user_id)
            .where(SalonFollower.follower == user_id)
        )
        query = query.filter(
            or_(
                Post.user_id == user_id,
                Post.user_id.in_(followed_users),
            )
        )

    elif option == PostCollectionType.trending:
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
        pass

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post collection type",
        )

    if cursor_dt:
        query = query.filter(Post.created_at < cursor_dt)

    posts = (
        query.order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

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
                "author": {
                    "user_id": author.id,
                    "username": author.username,
                    "is_verified": author.is_verified,
                    "profile_picture": (
                        f"{PROFILE_URL}{author.profile_picture.file_name}"
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
                        "url": f"{IMAGE_URL}{m.media_url}",
                        "type": m.media_type.name,
                        "aspect_ratio": m.aspect_ratio,
                    }
                    for m in post.media_items
                ],
                "service": post.sub_service.id,
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
    if settings.visibility != PostVisibility.PUBLIC:
        if post.user_id != user_id:
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
        "author": {
            "user_id": author.id,
            "username": author.username,
            "is_verified": author.is_verified,
            "profile_picture": (
                f"{PROFILE_URL}{author.profile_picture.file_name}"
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
                "url": f"{IMAGE_URL}{m.media_url}",
                "type": m.media_type.name,
                "aspect_ratio": m.aspect_ratio,
            }
            for m in post.media_items
        ],
        "service": post.sub_service.id,
        "stats": { 
            "likes": likes or 0, 
            "comments": comments or 0, 
            "shares": shares or 0, 
        },
        "viewer_state": {
            "is_liked": is_liked,
            "is_saved": is_saved,
            "is_my_post": post.user_id == user_id,
        },
        "created_at": post.created_at,
    }
    
    

def _map_post_to_post_response_schema(raw: Dict[str, Any]) -> Dict[str, Any]:
    author = raw["author"]
    salon = author.get("salon")
    address = salon.get("address") if salon else None

    return {
        "id": raw["id"],

        "author": {
            "id": author["user_id"],
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
        name=service_price.service_id.name,
        price=PriceRange(
            min=service_price.price_min,
            max=service_price.price_max,
            currency=service_price.currency or "TZS",
        ),
        duration_minutes=service_price.duration_minutes,
        benefits=[b.title for b in benefits],
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
                "user_avatar": (
                    f"{PROFILE_URL}{r.user.profile_picture.file_name}"
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
def _post_to_preview(post: Post) -> PostPreview:
    media = post.media_items[0] if post.media_items else None
    return PostPreview(
        id=post.id,
        cover_image=f"{IMAGE_URL}{media.media_url}" if media else "",
    )
    
    
def _build_similar_section(
    db: Session,
    post: Post,
    limit: int = 6,
) -> SimilarSection:

    base_filters = [
        Post.status == PostStatus.PUBLISHED.name,
        Post.id != post.id,
    ]

    # ------------------------------------------------
    # 1) By Service (same sub-service)
    # ------------------------------------------------
    by_service_posts = (
        db.query(Post)
        .options(joinedload(Post.media_items))
        .filter(
            *base_filters,
            Post.sub_service_id == post.sub_service_id,
        )
        .limit(limit)
        .all()
    )

    # ------------------------------------------------
    # 2) By Stylist (REAL performer, not post owner)
    # ------------------------------------------------
    stylist_ids = (
        db.query(StylistService.stylist_id)
        .join(SalonServicePrice,
              StylistService.salon_service_price_id == SalonServicePrice.id)
        .filter(
            SalonServicePrice.sub_service_id == post.sub_service_id,
        )
        .subquery()
    )

    by_stylist_posts = (
        db.query(Post)
        .join(SalonServicePrice,
              SalonServicePrice.sub_service_id == Post.sub_service_id)
        .join(StylistService,
              StylistService.salon_service_price_id == SalonServicePrice.id)
        .options(joinedload(Post.media_items))
        .filter(
            *base_filters,
            StylistService.stylist_id.in_(stylist_ids),
        )
        .limit(limit)
        .all()
    )

    # ------------------------------------------------
    # 3) By Salon (same salon, any stylist)
    # ------------------------------------------------
    by_salon_posts = []

    salon = db.query(Salon).filter(Salon.user_id == post.user_id).first()
    if salon:
        by_salon_posts = (
            db.query(Post)
            .join(User, User.id == Post.user_id)
            .join(Salon, Salon.user_id == User.id)
            .options(joinedload(Post.media_items))
            .filter(
                *base_filters,
                Salon.id == salon.id,
            )
            .limit(limit)
            .all()
        )

    return SimilarSection(
        by_service=[_post_to_preview(p) for p in by_service_posts],
        by_stylist=[_post_to_preview(p) for p in by_stylist_posts],
        by_salon=[_post_to_preview(p) for p in by_salon_posts],
    )




# Other Posts 
def _build_other_posts_section(
    db: Session,
    viewer_user_id: str,
    post: Post,
    exclude_post_ids: set[str],
    cursor: Optional[datetime] = None,
    limit: int = 10,
) -> OtherPostsSection:

    query = (
        db.query(Post)
        .join(User, Post.user_id == User.id)
        .outerjoin(Salon, Salon.user_id == User.id)
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
        )
    )

    # cursor pagination (THIS WAS MISSING)
    if cursor:
        query = query.filter(Post.created_at < cursor)

    signals = []

    if post.sub_service_id:
        signals.append(Post.sub_service_id == post.sub_service_id)

    salon = db.query(Salon).filter(Salon.user_id == post.user_id).first()
    if salon:
        signals.append(Salon.id == salon.id)

    if salon and salon.location and salon.location.region:
        signals.append(SalonLocation.region == salon.location.region)

    if signals:
        query = query.filter(or_(*signals))

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
    salon_id: Optional[str],
) -> List[StylistSection]:

    if not salon_id:
        return []

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        return []

    owner = (
        db.query(User)
        .options(joinedload(User.profile_picture))
        .filter(User.id == salon.user_id)
        .first()
    )

    if not owner:
        return []

    return [
        StylistSection(
            id=owner.id,
            name=owner.username,
            avatar=(
                f"{PROFILE_URL}{owner.profile_picture.file_name}"
                if owner.profile_picture
                else None
            ),
            title=None,
            rating=None,
        )
    ]



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
# SINGLE POST VIEW (AGGREGATED)
# Step 1: build post section (reuse get_post__)
# ==============================================================
async def get_single_post_view_(
    current_user: str,
    post_id: str,
    db: Session,
    other_cursor: Optional[datetime] = None,
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
    
    salon_id = post.user.salon.id if post.user and post.user.salon else None

    stylists = _build_stylists_section(
        db=db,
        salon_id=salon_id,
    )



    reviews = _build_review_section(
        db=db,
        salon_service_price_id=service.id if service.id else None,
    )


    similar = _build_similar_section(
        db=db,
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
        can_comment=True,  # keep True for now; later you can restrict if needed
    )

    booking = _build_booking_state(
        db=db,
        current_user=current_user,
        post=post,
        service_price_id=service.id if service.id else None,
    )
    
    # 
    exclude_ids = {post.id}

    exclude_ids.update(p.id for p in similar.by_service)
    exclude_ids.update(p.id for p in similar.by_stylist)
    exclude_ids.update(p.id for p in similar.by_salon)

    sponsored_salons = _build_sponsored_salons_section(db=db)

    other_posts = _build_other_posts_section(
        db=db,
        viewer_user_id=current_user.user_id,
        post=post,
        exclude_post_ids=exclude_ids,
        cursor=other_cursor,
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
