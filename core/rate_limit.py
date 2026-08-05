"""Provides the Rate Limit shared infrastructure module for the backend application."""

import time
from collections import deque
from threading import Lock
from typing import Deque

from fastapi import HTTPException, Request, status


_buckets: dict[str, Deque[float]] = {}
_lock = Lock()


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
    user_id: str | None = None,
) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds
    identity = user_id or _client_key(request)
    key = f"{bucket}:{identity}"

    with _lock:
        hits = _buckets.setdefault(key, deque())
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = max(1, int(window_seconds - (now - hits[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)


def rate_limit(*, bucket: str, limit: int, window_seconds: int):
    def dependency(request: Request) -> None:
        enforce_rate_limit(
            request,
            bucket=bucket,
            limit=limit,
            window_seconds=window_seconds,
        )

    return dependency
