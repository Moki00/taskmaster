"""Tests for the frontend simulation endpoint - now backed by the real 5-agent pipeline. Gemini is
mocked via the shared `mock_gemini` fixture (see conftest.py); routing, persistence, and response
shaping all run for real.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.intake_agent import _LanguageDetection
from app.agents.scheduler_agent import _SchedulingDecision
from app.api.routes import simulate
from app.main import app
from app.models import Classification, ReplyDraft, Urgency
from app.services.repository import get_repository


def _install_mocks(mock_gemini, sample_classification, sample_reply):
    mock_gemini(
        {
            _LanguageDetection: lambda: _LanguageDetection(language="en"),
            Classification: lambda: sample_classification,
            ReplyDraft: lambda: sample_reply,
            _SchedulingDecision: lambda: _SchedulingDecision(
                needs_appointment=False, appointment_type=None, reasoning="test"
            ),
        }
    )


async def test_simulation_creates_ticket_and_returns_result(mock_gemini, sample_classification, sample_reply):
    _install_mocks(mock_gemini, sample_classification, sample_reply)
    payload = simulate.SimulationRequest(
        client_name="Alice Smith",
        message="Our network switch is down and the office is in an outage.",
    )

    result = await simulate.run_simulation(payload)

    assert result.client == "Alice Smith"
    assert result.category == "Network"
    assert result.urgency == "Critical / High"
    assert result.device_type == "Network Switch"
    assert result.summary == sample_classification.summary
    assert result.ticket_number.startswith("TK-")
    assert len(result.logs) == 5
    assert [log["id"] for log in result.logs] == ["1", "2", "3", "4", "5"]
    assert all(log["status"] == "ok" for log in result.logs)
    assert result.draft_reply == sample_reply.body

    repo = get_repository()
    ticket = await repo.get_ticket(result.ticket_number, vertical="it_support")
    assert ticket is not None
    assert ticket.customer.name == "Alice Smith"
    assert ticket.description == payload.message
    assert ticket.priority == Urgency.CRITICAL


def test_simulate_endpoint_smoke_contract(mock_gemini, sample_classification, sample_reply):
    """The simulation route is the core live-demo endpoint. Keep its response shape stable and
    frontend-compatible so the dashboard never receives an incompatible payload."""
    _install_mocks(mock_gemini, sample_classification, sample_reply)
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

    expected_keys = {
        "timestamp",
        "client",
        "category",
        "urgency",
        "device_type",
        "summary",
        "ticket_number",
        "draft_reply",
        "logs",
    }
    assert expected_keys.issubset(payload)
    assert payload["client"] == "Alice Smith"
    assert payload["category"] == "Network"
    assert payload["urgency"] == "Critical / High"
    assert payload["ticket_number"].startswith("TK-")
    assert isinstance(payload["draft_reply"], str) and payload["draft_reply"]
    assert isinstance(payload["logs"], list) and len(payload["logs"]) >= 4
    assert all({"id", "time", "text", "status"}.issubset(log) for log in payload["logs"])
    assert all(log["status"] == "ok" for log in payload["logs"])
