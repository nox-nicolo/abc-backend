from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.account.audit import UserAuditEvent


def record_audit_event(
    db: Session,
    *,
    user_id: str,
    event_type: str,
    title: str,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> UserAuditEvent:
    event = UserAuditEvent(
        user_id=user_id,
        event_type=event_type,
        title=title,
        description=description,
        event_metadata=metadata or {},
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event


def list_audit_events(
    db: Session,
    *,
    user_id: str,
    limit: int = 30,
    offset: int = 0,
) -> dict:
    query = db.query(UserAuditEvent).filter(UserAuditEvent.user_id == user_id)
    total = query.count()
    rows = (
        query.order_by(UserAuditEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_event_out(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _event_out(event: UserAuditEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "metadata": dict(event.event_metadata or {}),
        "created_at": event.created_at,
    }
