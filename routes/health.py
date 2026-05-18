import os
from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import urlparse

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from core.database import SessionLocal
from core.r2_config import BUCKET_NAME, R2_ENDPOINT, s3
from service.notification.push import _credential_source, _firebase_app

health = APIRouter(prefix="/health", tags=["Health"])


@health.get("/live")
def liveness() -> dict:
    return {
        "status": "ok",
        "service": "abc-backend",
        "time": _now(),
    }


@health.get("/ready")
def readiness(response: Response) -> dict:
    checks = {
        "database": _check_database(),
        "r2": _check_r2(),
        "firebase": _check_firebase(),
        "redis": _check_redis(),
        "celery": _check_celery(),
    }
    ready = all(item["status"] in {"ok", "skipped"} for item in checks.values())

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "service": "abc-backend",
        "time": _now(),
        "checks": checks,
    }


@health.get("")
def health_summary(response: Response) -> dict:
    return readiness(response)


def _check_database() -> dict:
    started = perf_counter()
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return _ok(started)
    except Exception as exc:
        return _fail(started, exc)
    finally:
        db.close()


def _check_r2() -> dict:
    started = perf_counter()
    if not (R2_ENDPOINT and BUCKET_NAME):
        return _skipped(started, "R2_ENDPOINT and R2_BUCKET are not configured")

    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        return _ok(started)
    except Exception as exc:
        return _fail(started, exc)


def _check_firebase() -> dict:
    started = perf_counter()
    credential_source = _credential_source()
    if credential_source is None:
        return _skipped(started, "Firebase Admin credentials are not configured")

    try:
        app = _firebase_app()
        if app is None:
            return _fail(started, RuntimeError("Firebase Admin is not ready"))
        return {
            **_ok(started),
            "credential_source": credential_source,
        }
    except Exception as exc:
        return _fail(started, exc)


def _check_redis() -> dict:
    started = perf_counter()
    redis_url = _redis_url()
    if redis_url is None:
        return _skipped(started, "Redis/Celery is not configured")

    try:
        from redis import Redis
    except Exception as exc:
        return _fail(started, exc)

    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        client.close()
        return {
            **_ok(started),
            "url": _safe_url(redis_url),
        }
    except Exception as exc:
        return _fail(started, exc, extra={"url": _safe_url(redis_url)})


def _check_celery() -> dict:
    started = perf_counter()
    if not _background_jobs_enabled():
        return _skipped(started, "Background jobs are disabled")

    broker_url = _redis_url()
    if broker_url is None:
        return _fail(started, RuntimeError("Celery broker is not configured"))

    try:
        from worker.celery_app import celery_app
    except Exception as exc:
        return _fail(started, exc)

    try:
        connection = celery_app.connection_for_read()
        connection.ensure_connection(max_retries=1, timeout=2)
        connection.close()
        return {
            **_ok(started),
            "broker": _safe_url(str(celery_app.conf.broker_url)),
        }
    except Exception as exc:
        return _fail(
            started,
            exc,
            extra={"broker": _safe_url(str(celery_app.conf.broker_url))},
        )


def _redis_url() -> str | None:
    broker_url = os.getenv("CELERY_BROKER_URL")
    result_backend = os.getenv("CELERY_RESULT_BACKEND")
    redis_url = os.getenv("REDIS_URL")
    return broker_url or result_backend or redis_url


def _background_jobs_enabled() -> bool:
    value = os.getenv("BACKGROUND_JOBS_ENABLED")
    if value is not None:
        return value.lower() in {"1", "true", "yes"}
    if os.getenv("CELERY_BROKER_URL") is not None:
        return True
    return False


def _ok(started: float) -> dict:
    return {"status": "ok", "latency_ms": _elapsed_ms(started)}


def _skipped(started: float, reason: str) -> dict:
    return {
        "status": "skipped",
        "reason": reason,
        "latency_ms": _elapsed_ms(started),
    }


def _fail(started: float, exc: Exception, *, extra: dict | None = None) -> dict:
    data = {
        "status": "fail",
        "error": exc.__class__.__name__,
        "message": str(exc),
        "latency_ms": _elapsed_ms(started),
    }
    if extra:
        data.update(extra)
    return data


def _elapsed_ms(started: float) -> int:
    return round((perf_counter() - started) * 1000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme:
        return "configured"
    host = parsed.hostname or "configured"
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path if parsed.path else ""
    return f"{parsed.scheme}://{host}{port}{path}"
