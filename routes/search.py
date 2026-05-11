
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from models.search.search import SearchHistory
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.search.hashtag import HashtagGridOut
from pydantic_schemas.search.search import SaveSearchHistoryRequest, SaveSearchHistoryResponse, SearchResponse
from service.auth.JWT.oauth2 import get_current_user
from service.search.discover import get_nearby_salons, get_top_salons, get_trending_styles
from service.search.search import search_
from service.search.hashtag import get_hashtag_grid_

search = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@search.get(
    "",
    summary="Global search across users, salons, posts, hashtags, services",
)
async def global_search(
    q: str = Query(
        ...,
        min_length=1,
        description="Search query text"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=50,
        description="Max number of results"
    ),
    cursor: str | None = Query(
        None,
        description="Cursor for pagination (optional)"
    ),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Global search endpoint.

    - Searches across users, salons, posts, hashtags, services
    - Returns polymorphic results
    - Frontend determines navigation using `entity`
    """
    return await search_(
        q=q,
        limit=limit,
        cursor=cursor,
        db=db,
        user_id=current_user.user_id,
    )
    

# ── Discovery endpoints (idle search screen) ────────────────────────────────

@search.get("/nearby", summary="Salons near a given coordinate")
def nearby_salons(
    lat: float = Query(
        ..., ge=-90, le=90, description="Latitude of the customer"
    ),
    lng: float = Query(
        ..., ge=-180, le=180, description="Longitude of the customer"
    ),
    radius_km: float = Query(15.0, ge=1, le=100),
    limit: int = Query(10, ge=1, le=30),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return get_nearby_salons(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        limit=limit,
        offset=offset,
        current_user_id=current_user.user_id,
    )


@search.get("/top-salons", summary="Top salons by number of bookings")
def top_salons(
    limit: int = Query(10, ge=1, le=30),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return get_top_salons(
        db=db,
        current_user_id=current_user.user_id,
        limit=limit,
        offset=offset,
    )


@search.get("/trending", summary="Trending hashtag styles in the last 30 days")
def trending_styles(
    limit: int = Query(10, ge=1, le=30),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return get_trending_styles(db=db, limit=limit, offset=offset)


# Search Result
@search.get(
    "/hashtags",
    response_model=HashtagGridOut,
)
async def get_hashtag(
    id: str = Query(..., min_length=1, max_length=50),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Returns hashtag header info and a grid of post image previews
    """
    return await get_hashtag_grid_(
        hashtag_id= id,
        db= db,
        cursor= cursor,
        limit= limit,
        user = current_user.user_id
    )
