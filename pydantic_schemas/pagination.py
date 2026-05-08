from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginationMeta(BaseModel):
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    next_offset: Optional[int] = None
    has_more: bool


class Page(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMeta


def pagination_meta(*, total: int, limit: int, offset: int) -> PaginationMeta:
    next_offset = offset + limit
    has_more = next_offset < total
    return PaginationMeta(
        limit=limit,
        offset=offset,
        total=total,
        next_offset=next_offset if has_more else None,
        has_more=has_more,
    )
