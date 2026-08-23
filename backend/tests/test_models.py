"""Round-trip and invalid-payload tests for the app.models contract."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    Appointment,
    AppointmentStatus,
    Channel,
    Classification,
    NormalizedMessage,
    PipelineState,
    ReplyDraft,
    Sender,
    Sentiment,
    StageTiming,
    Ticket,
    TicketStatus,
    TimeSlot,
    Urgency,
)


# --- sample builders -------------------------------------------------------


def sample_message() -> NormalizedMessage:
    return NormalizedMessage(
        intake_id="intake-1",
        vertical="it_support",
        channel=Channel.EMAIL,
        sender=Sender(name="Jane Doe", email="jane@example.com"),
        subject="My printer is broken",
        body_text="The printer on the 3rd floor won't turn on.",
    )


def sample_classification() -> Classification:
    return Classification(
        issue_type="hardware_failure",
        urgency=Urgency.HIGH,
        summary="Printer on 3rd floor is unresponsive.",
        extracted_details={"device": "printer", "floor": 3},
        missing_info=["asset_tag"],
        sentiment=Sentiment.ANNOYED,
        frustration_score=0.4,
        business_impact="Team cannot print client documents.",
        confidence=0.87,
        reasoning="Message clearly describes a non-functioning hardware device.",
    )


def sample_ticket() -> Ticket:
    return Ticket(
        ticket_number="TCK-0001",
        intake_id="intake-1",
        vertical="it_support",
        customer=Sender(name="Jane Doe", email="jane@example.com"),
        issue_type="hardware_failure",
        priority=Urgency.HIGH,
        status=TicketStatus.NEW,
        title="Printer unresponsive on 3rd floor",
        description="The printer on the 3rd floor won't turn on.",
        extracted_details={"device": "printer", "floor": 3},
        missing_info=["asset_tag"],
        sentiment=Sentiment.ANNOYED,
        confidence=0.87,
    )


def sample_reply() -> ReplyDraft:
    return ReplyDraft(
        subject="Re: My printer is broken",
        body="Thanks for reaching out - we've logged ticket TCK-0001 and will follow up shortly.",
        tone="empathetic",
        language="en",
        questions_asked=["What is the printer's asset tag?"],
    )


def sample_appointment() -> Appointment:
    start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    return Appointment(
        appointment_id="appt-1",
        ticket_number="TCK-0001",
        appointment_type="on_site_repair",
        assignee="tech-42",
        proposed_slots=[TimeSlot(start=start, end=end)],
        status=AppointmentStatus.PROPOSED,
    )


def sample_pipeline_state() -> PipelineState:
    return PipelineState(
        message=sample_message(),
        classification=sample_classification(),
        ticket=sample_ticket(),
        reply=sample_reply(),
        appointment=sample_appointment(),
        stage_timings=[
            StageTiming(stage="intake_agent", elapsed_ms=120.5, correlation_id="intake-1")
        ],
    )


# --- round-trip tests --------------------------------------------------------


def test_normalized_message_round_trip():
    original = sample_message()
    restored = NormalizedMessage.model_validate_json(original.model_dump_json())
    assert restored == original


def test_classification_round_trip():
    original = sample_classification()
    restored = Classification.model_validate_json(original.model_dump_json())
    assert restored == original


def test_ticket_round_trip():
    original = sample_ticket()
    restored = Ticket.model_validate_json(original.model_dump_json())
    assert restored == original


def test_reply_draft_round_trip():
    original = sample_reply()
    restored = ReplyDraft.model_validate_json(original.model_dump_json())
    assert restored == original


def test_appointment_round_trip():
    original = sample_appointment()
    restored = Appointment.model_validate_json(original.model_dump_json())
    assert restored == original


def test_pipeline_state_round_trip():
    original = sample_pipeline_state()
    restored = PipelineState.model_validate_json(original.model_dump_json())
    assert restored == original


# --- invalid payload tests ----------------------------------------------------


def test_normalized_message_missing_body_text_is_invalid():
    payload = sample_message().model_dump(mode="json")
    del payload["body_text"]
    with pytest.raises(ValidationError):
        NormalizedMessage.model_validate(payload)


def test_classification_confidence_out_of_range_is_invalid():
    payload = sample_classification().model_dump(mode="json")
    payload["confidence"] = 1.5
    with pytest.raises(ValidationError):
        Classification.model_validate(payload)


def test_ticket_invalid_status_is_invalid():
    payload = sample_ticket().model_dump(mode="json")
    payload["status"] = "not_a_status"
    with pytest.raises(ValidationError):
        Ticket.model_validate(payload)


def test_reply_draft_missing_body_is_invalid():
    payload = sample_reply().model_dump(mode="json")
    del payload["body"]
    with pytest.raises(ValidationError):
        ReplyDraft.model_validate(payload)


def test_appointment_slot_end_before_start_is_invalid():
    start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        TimeSlot(start=start, end=start - timedelta(minutes=30))


def test_pipeline_state_negative_elapsed_ms_is_invalid():
    payload = sample_pipeline_state().model_dump(mode="json")
    payload["stage_timings"][0]["elapsed_ms"] = -5
    with pytest.raises(ValidationError):
        PipelineState.model_validate(payload)


# --- vertical taxonomy context validation -------------------------------------


def test_issue_type_passes_when_in_context_taxonomy():
    payload = sample_classification().model_dump(mode="json")
    result = Classification.model_validate(
        payload, context={"valid_issue_types": {"hardware_failure", "network_outage"}}
    )
    assert result.issue_type == "hardware_failure"


def test_issue_type_rejected_when_not_in_context_taxonomy():
    payload = sample_classification().model_dump(mode="json")
    with pytest.raises(ValidationError):
        Classification.model_validate(
            payload, context={"valid_issue_types": {"network_outage", "account_access"}}
        )
