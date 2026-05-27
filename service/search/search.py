# service/search/search.py

from __future__ import annotations

from sqlalchemy.orm import Session

from models.search.search import SearchHistory
from models.booking.booking import Booking
from models.profile.salon import SalonFollower
from models.saved import SavedSalon
from pydantic_schemas.search.search import SaveSearchHistoryResponse, SearchResponse
from service.account.enforcement import customer_recommendation_controls

from service.search.queries import (
    search_users,
    search_salons,
    search_hashtags,
    search_services,
)


async def search_(
    q: str,
    limit: int,
    cursor: str | None,
    db: Session,
    user_id: str,   
) -> SearchResponse:
    results = []
    controls = customer_recommendation_controls(db, user_id)

    # Collect candidates from all sources
    results.extend(search_users(db, q, limit, user_id))
    results.extend(search_salons(db, q, limit, user_id))
    if controls.show_trending:
        results.extend(search_hashtags(db, q, limit))
    results.extend(search_services(db, q, limit, user_id))

    # Final ranking (single truth)
    results.sort(
        key=lambda x: _personalized_score(db, user_id, x, controls),
        reverse=True,
    )

    # TODO: cursor pagination can be added later (score+id based)
    return SearchResponse(results=results)


def _personalized_score(db: Session, user_id: str, result, controls) -> float:
    score = float(getattr(result, "score", 0) or 0)
    if getattr(result, "entity", None) != "salon":
        return score

    salon_id = getattr(result, "id", None)
    if not salon_id:
        return score

    if controls.use_saved:
        saved = (
            db.query(SavedSalon.id)
            .filter(SavedSalon.user_id == user_id, SavedSalon.salon_id == salon_id)
            .first()
        )
        if saved:
            score += 15

    if controls.use_following:
        following = (
            db.query(SalonFollower.id)
            .filter(SalonFollower.user_id == user_id, SalonFollower.salon_id == salon_id)
            .first()
        )
        if following:
            score += 12

    if controls.use_bookings:
        booked = (
            db.query(Booking.id)
            .filter(Booking.customer_id == user_id, Booking.salon_id == salon_id)
            .first()
        )
        if booked:
            score += 10

    return score


async def save_search_history_(
    db: Session,
    user_id: str,
    query: str,
    entity: str,
    entity_id: str | None,  
) -> SaveSearchHistoryResponse:
    history = SearchHistory(
        user_id=user_id,
        query=query,
        entity=entity,
        entity_id=entity_id,
    )

    db.add(history)
    db.commit()

    return SaveSearchHistoryResponse(success=True)


# These are product enhancements, not backend correctness fixes:

# cursor-based pagination by (score, id)

# analytics / search metrics

# click-through feedback loop

# caching hot queries

# FTS or trigram indexes
