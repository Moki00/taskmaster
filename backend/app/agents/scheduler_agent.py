"""Scheduler Agent: decides if an appointment is needed, checks Google Calendar availability,
proposes slots, confirms the earliest one, and blocks it - the fully autonomous, no-human-in-the-
loop finish of the pipeline for requests that need a scheduled visit or call.

Skips entirely (no Gemini call, no Calendar call) when the active vertical defines no appointment
types at all. Degrades gracefully - never raises - when Calendar isn't configured or unavailable,
since that's expected in local/demo environments without real Google credentials.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog

from app.core.errors import IntegrationError
from app.core.timing import timed_stage
from app.integrations.calendar_client import get_calendar_client
from app.integrations.gemini_client import get_gemini_client
from app.models.appointment import Appointment
from app.models.base import TaskmasterModel
from app.models.classification import Classification
from app.models.enums import AppointmentStatus, TicketStatus
from app.models.message import NormalizedMessage
from app.models.ticket import Ticket, TicketHistoryEntry
from app.services.repository import get_repository
from app.verticals.base import AppointmentType, VerticalConfig
from app.verticals.loader import get_active_vertical

log = structlog.get_logger("taskmaster.scheduler_agent")

_SEARCH_WINDOW_DAYS = 7
_MAX_PROPOSED_SLOTS = 3


class _SchedulingDecision(TaskmasterModel):
    needs_appointment: bool
    appointment_type: str | None = None
    reasoning: str


def _build_system_prompt(vertical: VerticalConfig, classification: Classification) -> str:
    type_lines = "\n".join(
        f"- {t.name} ({t.duration_minutes} min, {'onsite' if t.requires_onsite else 'remote'}): {t.triggers_when}"
        for t in vertical.appointment_types
    )
    return f"""You decide whether a customer request for {vertical.display_name} needs a scheduled
appointment, and if so which type.

Available appointment types:
{type_lines}

The request has been classified as issue_type='{classification.issue_type}',
urgency='{classification.urgency.value}', business_impact='{classification.business_impact}'.
Summary: {classification.summary}

Decide:
- `needs_appointment`: true only if resolving this genuinely requires a scheduled session matching
  one of the trigger conditions above - not for anything that can be resolved by an async reply alone.
- `appointment_type`: the exact name of the matching type above, or null if no appointment is needed.
- `reasoning`: one sentence explaining the decision."""


def _resolve_appointment_type(vertical: VerticalConfig, name: str | None) -> AppointmentType:
    if name:
        for t in vertical.appointment_types:
            if t.name == name:
                return t
        log.warning("scheduler_agent_unknown_appointment_type", requested=name)
    return vertical.appointment_types[0]


async def _log_skip(ticket: Ticket, vertical: VerticalConfig, notes: str, *, correlation_id: str) -> None:
    repo = get_repository()
    await repo.append_ticket_event(
        ticket.ticket_number,
        vertical=vertical.key,
        entry=TicketHistoryEntry(
            actor="scheduler_agent",
            action="scheduling_skipped",
            notes=notes,
            agent_name="scheduler_agent",
            correlation_id=correlation_id,
        ),
    )


async def run(
    message: NormalizedMessage,
    classification: Classification,
    ticket: Ticket,
    *,
    vertical: VerticalConfig | None = None,
    correlation_id: str | None = None,
) -> Appointment | None:
    """Returns a confirmed Appointment if one was booked, or None if no appointment was needed or
    Calendar wasn't reachable. Never raises - scheduling is a bonus stage, not a hard dependency
    for the ticket already created upstream.
    """
    vertical = vertical or get_active_vertical()
    cid = correlation_id or message.intake_id

    if not vertical.appointment_types:
        return None

    async with timed_stage("scheduler_agent", correlation_id=cid, vertical=vertical.key):
        gemini = get_gemini_client()
        decision = await gemini.generate_structured(
            system_prompt=_build_system_prompt(vertical, classification),
            user_content=f"{classification.summary}\n\n{message.body_text}",
            response_schema=_SchedulingDecision,
            correlation_id=cid,
        )

        if not decision.needs_appointment:
            return None

        appointment_type = _resolve_appointment_type(vertical, decision.appointment_type)

        now = datetime.now(timezone.utc)
        try:
            calendar = get_calendar_client()
            slots = await calendar.get_available_slots(
                start=now,
                end=now + timedelta(days=_SEARCH_WINDOW_DAYS),
                duration_minutes=appointment_type.duration_minutes,
                correlation_id=cid,
            )
        except IntegrationError as exc:
            log.warning("scheduler_agent_calendar_unavailable", error=str(exc))
            await _log_skip(ticket, vertical, f"Calendar unavailable: {exc}", correlation_id=cid)
            return None

        if not slots:
            await _log_skip(
                ticket,
                vertical,
                f"No availability found for {appointment_type.name} in the next {_SEARCH_WINDOW_DAYS} days.",
                correlation_id=cid,
            )
            return None

        proposed_slots = slots[:_MAX_PROPOSED_SLOTS]
        first_slot = proposed_slots[0]
        appointment_id = f"appt-{uuid.uuid4().hex[:8]}"

        try:
            event_id = await calendar.create_event(
                slot=first_slot,
                summary=f"Ticket #{ticket.ticket_number}: {appointment_type.name}",
                description=ticket.description,
                correlation_id=cid,
            )
        except IntegrationError as exc:
            log.warning("scheduler_agent_booking_failed", error=str(exc))
            appointment = Appointment(
                appointment_id=appointment_id,
                ticket_number=ticket.ticket_number,
                vertical=vertical.key,
                appointment_type=appointment_type.name,
                assignee=ticket.assigned_to,
                proposed_slots=proposed_slots,
                status=AppointmentStatus.PROPOSED,
            )
            repo = get_repository()
            await repo.save_appointment(appointment)
            await _log_skip(ticket, vertical, f"Slots proposed but booking failed: {exc}", correlation_id=cid)
            return appointment

        appointment = Appointment(
            appointment_id=appointment_id,
            ticket_number=ticket.ticket_number,
            vertical=vertical.key,
            appointment_type=appointment_type.name,
            assignee=ticket.assigned_to,
            proposed_slots=proposed_slots,
            confirmed_slot=first_slot,
            calendar_event_id=event_id,
            status=AppointmentStatus.CONFIRMED,
        )

        repo = get_repository()
        await repo.save_appointment(appointment)
        await repo.update_ticket_status(
            ticket.ticket_number,
            vertical=vertical.key,
            status=TicketStatus.SCHEDULED,
            actor="scheduler_agent",
            agent_name="scheduler_agent",
            correlation_id=cid,
            notes=f"Appointment {appointment_id} confirmed for {first_slot.start.isoformat()}",
        )
        return appointment
