"""Provides the Gunicorn.Conf application module for the backend application."""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
worker_class = "uvicorn.workers.UvicornWorker"

# Tune WEB_CONCURRENCY for the paid instance size. Start at 2 workers, then
# raise gradually while watching memory, p95 latency, and database connections.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("WEB_THREADS", "2"))
timeout = int(os.getenv("WEB_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("WEB_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("WEB_KEEPALIVE", "5"))

# Recycle occasionally so memory fragmentation or SDK caches do not accumulate
# forever on a small instance.
max_requests = int(os.getenv("WEB_MAX_REQUESTS", "500"))
max_requests_jitter = int(os.getenv("WEB_MAX_REQUESTS_JITTER", "50"))

preload_app = os.getenv("WEB_PRELOAD", "false").lower() == "true"
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
