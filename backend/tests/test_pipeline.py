"""End-to-end tests for the 5-agent pipeline (app/agents/pipeline.py). Gemini is mocked via the
shared `mock_gemini` fixture (see conftest.py); everything else (routing, persistence, taxonomy
validation, timing) runs for real against InMemoryRepo (ENV=local).
"""
from __future__ import annotations

import pytest

from app.agents import pipeline
from app.agents.intake_agent import IntakeInput, _LanguageDetection
from app.agents.scheduler_agent import _SchedulingDecision
from app.models import Channel, Classification, ReplyDraft, Sender, Urgency
from app.services.repository import get_repository
from app.verticals.loader import get_active_vertical


def _intake_input() -> IntakeInput:
    vertical = get_active_vertical()
    return IntakeInput(
        channel=Channel.WEB_FORM,
        vertical=vertical.key,
        sender=Sender(name="Alice Smith", email="alice@example.com"),
        body_text="Our main switch is down and the office network is completely dead!",
    )


async def test_pipeline_runs_end_to_end_without_appointment(mock_gemini, sample_classification, sample_reply):
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

    state = await pipeline.run(_intake_input())

    assert state.message.body_text.startswith("Our main switch is down")
    assert state.classification is not None and state.classification.issue_type == "network"
    assert state.ticket is not None
    assert state.ticket.ticket_number.startswith("TK-")
    assert state.ticket.priority == Urgency.CRITICAL
    assert state.ticket.assigned_to == "senior_network_engineer"
    assert state.reply is not None and "technician" in state.reply.body
    assert state.appointment is None
    assert not state.errors

    # stage_timings also picks up nested gemini.generate_structured calls made within each agent -
    # that's expected (timed_stage nests) and useful: it shows Gemini's own latency contribution.
    stage_names = {t.stage for t in state.stage_timings}
    assert {"intake_agent", "classifier_agent", "ticket_agent", "reply_agent", "scheduler_agent"} <= stage_names
    assert all(t.correlation_id == state.message.intake_id for t in state.stage_timings)

    repo = get_repository()
    persisted = await repo.get_ticket(state.ticket.ticket_number, vertical=state.ticket.vertical)
    assert persisted is not None


async def test_pipeline_skips_scheduling_gracefully_when_calendar_unconfigured(
    monkeypatch: pytest.MonkeyPatch, mock_gemini, sample_classification, sample_reply
):
    from app.config import settings

    monkeypatch.setattr(settings, "CALENDAR_ID", None)
    mock_gemini(
        {
            _LanguageDetection: lambda: _LanguageDetection(language="en"),
            Classification: lambda: sample_classification,
            ReplyDraft: lambda: sample_reply,
            _SchedulingDecision: lambda: _SchedulingDecision(
                needs_appointment=True, appointment_type="remote_session", reasoning="test"
            ),
        }
    )

    state = await pipeline.run(_intake_input())

    assert state.ticket is not None
    assert state.appointment is None
    assert not state.errors  # scheduler_agent degrades gracefully, it doesn't raise

    repo = get_repository()
    ticket = await repo.get_ticket(state.ticket.ticket_number, vertical=state.ticket.vertical)
    assert any(entry.action == "scheduling_skipped" for entry in ticket.history)
