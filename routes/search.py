
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from models.search.search import SearchHistory
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.search.hashtag import HashtagGridOut
from pydantic_schemas.search.search import SaveSearchHistoryRequest, SaveSearchHistoryResponse, SearchResponse
from service.auth.JWT.oauth2 import get_current_user
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
