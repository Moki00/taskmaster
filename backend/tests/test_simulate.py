"""Tests for the frontend simulation endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import simulate
from app.main import app
from app.models import Urgency
from app.services.in_memory_repo import InMemoryRepo


async def test_simulation_creates_ticket_and_returns_result(monkeypatch):
    repo = InMemoryRepo()
    monkeypatch.setattr(simulate, "get_repository", lambda: repo)
    payload = simulate.SimulationRequest(
        client_name="Alice Smith",
        message="Our network switch is down and the office is in an outage.",
    )

    result = await simulate.run_simulation(payload)

    assert result.client == "Alice Smith"
    assert result.category == "Network"
    assert result.urgency == "Critical / High"
    assert result.device_type == "Network / Gateway"
    assert result.summary == payload.message
    assert result.ticket_number.startswith("TK-")
    assert len(result.logs) == 4
    assert [log["id"] for log in result.logs] == ["1", "2", "3", "4"]
    assert all(log["status"] == "ok" for log in result.logs)

    ticket = await repo.get_ticket(result.ticket_number, vertical="it_support")
    assert ticket is not None
    assert ticket.customer.name == "Alice Smith"
    assert ticket.description == payload.message
    assert ticket.priority == Urgency.CRITICAL


def test_simulate_endpoint_smoke_contract():
    """The simulation route is the core live-demo endpoint. Keep its response shape stable and
    frontend-compatible so the dashboard never receives an incompatible payload."""
    client = TestClient(app)
    response = client.post(
        "/api/simulate",
        json={
            "client_name": "Alice Smith",
            "message": "Our network switch is down and the office is in an outage.",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    expected_keys = {"timestamp", "client", "category", "urgency", "device_type", "summary", "ticket_number", "logs"}
    assert expected_keys.issubset(payload)
    assert payload["client"] == "Alice Smith"
    assert payload["category"] == "Network"
    assert payload["urgency"] == "Critical / High"
    assert payload["device_type"] == "Network / Gateway"
    assert payload["summary"] == "Our network switch is down and the office is in an outage."
    assert payload["ticket_number"].startswith("TK-")
    assert isinstance(payload["logs"], list) and len(payload["logs"]) >= 4
    assert all({"id", "time", "text", "status"}.issubset(log) for log in payload["logs"])
    assert all(log["status"] == "ok" for log in payload["logs"])
