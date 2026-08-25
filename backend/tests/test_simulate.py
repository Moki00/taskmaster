"""Tests for the frontend simulation endpoint."""
from __future__ import annotations

from app.api.routes import simulate
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
