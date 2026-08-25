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
    assert response.headers["X-Request-ID"]
