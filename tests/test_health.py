"""Provides the Test Health test module for the backend application."""

from fastapi import Response, status

import routes.health as health_routes


def _ok_component():
    return {"status": "ok", "latency_ms": 1}


def _skipped_component():
    return {"status": "skipped", "reason": "not configured", "latency_ms": 0}


def test_liveness_endpoint_is_lightweight():
    response = health_routes.liveness()

    assert response["status"] == "ok"


def test_readiness_returns_ready_when_required_checks_pass(monkeypatch):
    monkeypatch.setattr(health_routes, "_check_database", _ok_component)
    monkeypatch.setattr(health_routes, "_check_r2", _skipped_component)
    monkeypatch.setattr(health_routes, "_check_firebase", _skipped_component)
    monkeypatch.setattr(health_routes, "_check_redis", _skipped_component)
    monkeypatch.setattr(health_routes, "_check_celery", _skipped_component)
    response = Response()

    body = health_routes.readiness(response)

    assert response.status_code == status.HTTP_200_OK
    assert body["status"] == "ready"
    assert body["checks"]["database"]["status"] == "ok"


def test_readiness_returns_503_when_a_required_check_fails(monkeypatch):
    monkeypatch.setattr(health_routes, "_check_database", _ok_component)
    monkeypatch.setattr(
        health_routes,
        "_check_r2",
        lambda: {"status": "fail", "error": "Boom", "message": "nope"},
    )
    monkeypatch.setattr(health_routes, "_check_firebase", _skipped_component)
    monkeypatch.setattr(health_routes, "_check_redis", _skipped_component)
    monkeypatch.setattr(health_routes, "_check_celery", _skipped_component)
    response = Response()

    body = health_routes.readiness(response)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert body["status"] == "not_ready"
    assert body["checks"]["r2"]["status"] == "fail"
