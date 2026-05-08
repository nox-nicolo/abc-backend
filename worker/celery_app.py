import os

from celery import Celery
from celery.schedules import crontab


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "abc_backend",
    broker=os.getenv("CELERY_BROKER_URL", REDIS_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL),
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-auth-records-hourly": {
        "task": "worker.tasks.cleanup_expired_auth_records",
        "schedule": crontab(minute=0),
    },
    "scan-booking-reminders-every-5-minutes": {
        "task": "worker.tasks.scan_booking_reminders",
        "schedule": crontab(minute="*/5"),
    },
    "refresh-top-salon-ranking-every-15-minutes": {
        "task": "worker.tasks.refresh_top_salon_ranking",
        "schedule": crontab(minute="*/15"),
    },
}
