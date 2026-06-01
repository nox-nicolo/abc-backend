# Background Workers

The backend uses Celery with Redis for slow or scheduled work:

- verification emails
- push notification delivery
- expired auth cleanup
- booking status maintenance
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

## Redis-free booking maintenance

If Redis/Celery is not available yet, run booking status maintenance from server cron instead. Configure a strong shared secret:

```bash
MAINTENANCE_TOKEN=replace-with-a-long-random-secret
```

Then call the protected endpoint every minute from the server:

```bash
* * * * * curl -fsS -X POST \
  -H "X-Maintenance-Token: $MAINTENANCE_TOKEN" \
  https://YOUR_API_HOST/api/v1/health/maintenance/booking-status >/dev/null
```

This expires pending bookings and marks past confirmed bookings as no-show without requiring Redis. Keep Celery beat disabled until Redis is configured, otherwise both schedulers may run the same maintenance.
