"""Simulation endpoint for the frontend dashboard - runs the real 5-agent pipeline end to end
(Intake -> Classifier -> Ticket -> Reply -> Scheduler) against the active vertical. Response shape
is fixed by the frontend contract (frontend/src/App.jsx's handleSimulate) - keep field names as-is.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import pipeline
from app.agents.intake_agent import IntakeInput
from app.models import Channel, Sender, Urgency
from app.verticals import get_active_vertical

router = APIRouter(prefix="/api", tags=["simulation"])


class SimulationRequest(BaseModel):
    client_name: str = Field(default="Alice Smith")
    message: str


class SimulationResponse(BaseModel):
    timestamp: str
    client: str
    category: str
    urgency: str
    device_type: str
    summary: str
    ticket_number: str
    draft_reply: str
    logs: list[dict[str, str]]


def _format_urgency(urgency: Urgency) -> str:
    """Matches the display convention the frontend was already built against."""
    if urgency == Urgency.CRITICAL:
        return "Critical / High"
    return f"{urgency.value.title()} Priority"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _build_logs(state) -> list[dict[str, str]]:
    classification = state.classification
    ticket = state.ticket

    logs: list[dict[str, str]] = [
        {
            "id": "1",
            "time": _now(),
            "text": f"Intake Agent: Ingested message from {state.message.sender.name or 'customer'} via {state.message.channel.value}.",
            "status": "ok",
        },
        {
            "id": "2",
            "time": _now(),
            "text": (
                f"Classifier Agent: Category='{classification.issue_type}', "
                f"Urgency='{classification.urgency.value}' (confidence={classification.confidence:.0%})."
            ),
            "status": "ok",
        },
        {
            "id": "3",
            "time": _now(),
            "text": f"Ticket Agent: Created Ticket #{ticket.ticket_number} (assigned to {ticket.assigned_to}).",
            "status": "ok",
        },
        {
            "id": "4",
            "time": _now(),
            "text": (
                "Reply Agent: Draft response queued for client acknowledgment."
                if state.reply is not None
                else "Reply Agent: Failed to draft a response."
            ),
            "status": "ok" if state.reply is not None else "error",
        },
    ]

    if state.appointment is not None and state.appointment.confirmed_slot is not None:
        when = state.appointment.confirmed_slot.start.strftime("%Y-%m-%d %H:%M UTC")
        text = f"Scheduler Agent: Appointment confirmed for {when}."
    elif state.appointment is not None:
        text = f"Scheduler Agent: Slots proposed for {state.appointment.appointment_type}, awaiting confirmation."
    else:
        text = "Scheduler Agent: No appointment required for this request."
    logs.append({"id": "5", "time": _now(), "text": text, "status": "ok"})

    for error in state.errors:
        logs.append({"id": str(len(logs) + 1), "time": _now(), "text": f"{error.stage}: {error.message}", "status": "error"})

    return logs


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(payload: SimulationRequest) -> SimulationResponse:
    vertical = get_active_vertical()

    intake_input = IntakeInput(
        channel=Channel.WEB_FORM,
        vertical=vertical.key,
        sender=Sender(name=payload.client_name),
        body_text=payload.message,
    )

    try:
        state = await pipeline.run(intake_input, vertical=vertical)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {exc}") from exc

    classification = state.classification
    ticket = state.ticket
    if classification is None or ticket is None:
        # pipeline.run() raises before returning if either stage fails, so this is unreachable in
        # practice - guards the type checker and fails loudly instead of a confusing attribute error.
        raise HTTPException(status_code=502, detail="Pipeline completed without a classification or ticket.")

    return SimulationResponse(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        client=payload.client_name,
        category=classification.issue_type.replace("_", " ").title(),
        urgency=_format_urgency(classification.urgency),
        device_type=str(classification.extracted_details.get("device_type", "Not specified")),
        summary=classification.summary,
        ticket_number=ticket.ticket_number,
        draft_reply=state.reply.body if state.reply is not None else "Draft reply unavailable - see execution log.",
        logs=_build_logs(state),
    )
