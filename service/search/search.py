# service/search/search.py

from __future__ import annotations

from sqlalchemy.orm import Session

from models.search.search import SearchHistory
from pydantic_schemas.search.search import SaveSearchHistoryResponse, SearchResponse

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

    # Collect candidates from all sources
    results.extend(search_users(db, q, limit, user_id))
    results.extend(search_salons(db, q, limit, user_id))
    results.extend(search_hashtags(db, q, limit))
    results.extend(search_services(db, q, limit, user_id))

    # Final ranking (single truth)
    results.sort(key=lambda x: float(getattr(x, "score", 0) or 0), reverse=True)

    # TODO: cursor pagination can be added later (score+id based)
    return SearchResponse(results=results)


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