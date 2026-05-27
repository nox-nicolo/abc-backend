from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEventOut(BaseModel):
    id: str
    event_type: str
    title: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int
