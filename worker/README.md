# Background Workers

The backend uses Celery with Redis for slow or scheduled work:

- verification emails
- push notification delivery
- expired auth cleanup
- booking reminder scans
- salon ranking refreshes

## Environment

```bash
REDIS_URL=redis://localhost:6379/0
BACKGROUND_JOBS_ENABLED=true
```

`CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` can override `REDIS_URL`.

## Commands

Run API:

```bash
uvicorn main:app --reload
```

Run worker:

```bash
celery -A worker.celery_app.celery_app worker --loglevel=info
```

Run scheduler:

```bash
celery -A worker.celery_app.celery_app beat --loglevel=info
```

For production, run API, worker, and beat as separate processes/services.
