"""Tests for the application health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import APP_VERSION, app


client = TestClient(app)


def test_health_reports_runtime_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": APP_VERSION,
        "env": settings.ENV,
        "active_vertical": settings.ACTIVE_VERTICAL,
    }
    assert len(response.headers["X-Request-ID"]) > 0


def test_health_endpoint_smoke_contract():
    """The health endpoint is the minimum API check for the demo and should keep returning a
    stable JSON contract to any frontend or operator monitoring the service."""
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert set(["status", "version", "env", "active_vertical"]).issubset(payload)
    assert payload["status"] == "ok"
    assert payload["env"] == settings.ENV
    assert payload["active_vertical"] == settings.ACTIVE_VERTICAL
    assert response.headers["X-Request-ID"]
