"""Wires the 5-agent pipeline: Intake -> Classifier -> Ticket -> Reply -> Scheduler, threading a
single correlation_id through every stage and assembling the full PipelineState.

Intake, Classifier, and Ticket are load-bearing: without a NormalizedMessage, Classification, and
Ticket there is nothing to show the customer or the technician, so a failure in any of those
stages aborts the run (after persisting whatever partial state exists, for debugging). Reply and
Scheduler are best-effort - the ticket is the product's core deliverable, so a failure there is
recorded in PipelineState.errors but never loses the ticket already created.
"""
from __future__ import annotations

import uuid

import structlog

from app.agents import classifier_agent, intake_agent, reply_agent, scheduler_agent, ticket_agent
from app.agents.intake_agent import IntakeInput
from app.core.timing import StageEvent, event_bus
from app.models.pipeline import PipelineErrorEntry, PipelineEvent, PipelineState, StageTiming
from app.services.repository import get_repository
from app.verticals.base import VerticalConfig
from app.verticals.loader import get_active_vertical

log = structlog.get_logger("taskmaster.pipeline")


async def run(intake_input: IntakeInput, *, vertical: VerticalConfig | None = None) -> PipelineState:
    """Runs the full pipeline for one inbound message and returns the persisted PipelineState."""
    vertical = vertical or get_active_vertical()
    correlation_id = f"intake-{uuid.uuid4().hex[:8]}"
    repo = get_repository()

    stage_timings: list[StageTiming] = []
    events: list[PipelineEvent] = [
        PipelineEvent(event="pipeline_started", data={"channel": intake_input.channel.value, "vertical": vertical.key})
    ]
    errors: list[PipelineErrorEntry] = []

    def _on_stage_event(stage_event: StageEvent) -> None:
        if stage_event.correlation_id == correlation_id:
            stage_timings.append(
                StageTiming(
                    stage=stage_event.stage,
                    elapsed_ms=stage_event.elapsed_ms,
                    correlation_id=stage_event.correlation_id,
                )
            )

    unsubscribe = event_bus.subscribe(_on_stage_event)
    try:
        try:
            message = await intake_agent.run(intake_input, correlation_id=correlation_id)
        except Exception as exc:
            log.error("pipeline_intake_failed", correlation_id=correlation_id, error=str(exc))
            raise

        try:
            classification = await classifier_agent.run(message, vertical=vertical, correlation_id=correlation_id)
        except Exception as exc:
            errors.append(
                PipelineErrorEntry(stage="classifier_agent", message=str(exc), error_type=type(exc).__name__)
            )
            events.append(PipelineEvent(event="pipeline_failed", stage="classifier_agent", data={"error": str(exc)}))
            await repo.save_pipeline_state(
                PipelineState(message=message, stage_timings=stage_timings, events=events, errors=errors)
            )
            raise

        try:
            ticket = await ticket_agent.run(message, classification, vertical=vertical, correlation_id=correlation_id)
        except Exception as exc:
            errors.append(PipelineErrorEntry(stage="ticket_agent", message=str(exc), error_type=type(exc).__name__))
            events.append(PipelineEvent(event="pipeline_failed", stage="ticket_agent", data={"error": str(exc)}))
            await repo.save_pipeline_state(
                PipelineState(
                    message=message,
                    classification=classification,
                    stage_timings=stage_timings,
                    events=events,
                    errors=errors,
                )
            )
            raise

        reply = None
        try:
            reply = await reply_agent.run(
                message, classification, ticket, vertical=vertical, correlation_id=correlation_id
            )
        except Exception as exc:
            errors.append(PipelineErrorEntry(stage="reply_agent", message=str(exc), error_type=type(exc).__name__))
            log.error("pipeline_reply_failed", correlation_id=correlation_id, error=str(exc))

        appointment = None
        try:
            appointment = await scheduler_agent.run(
                message, classification, ticket, vertical=vertical, correlation_id=correlation_id
            )
        except Exception as exc:
            errors.append(
                PipelineErrorEntry(stage="scheduler_agent", message=str(exc), error_type=type(exc).__name__)
            )
            log.error("pipeline_scheduler_failed", correlation_id=correlation_id, error=str(exc))

        events.append(PipelineEvent(event="pipeline_completed", data={"ticket_number": ticket.ticket_number}))
        state = PipelineState(
            message=message,
            classification=classification,
            ticket=ticket,
            reply=reply,
            appointment=appointment,
            stage_timings=stage_timings,
            events=events,
            errors=errors,
        )
        await repo.save_pipeline_state(state)

        log.info(
            "pipeline_run_completed",
            correlation_id=correlation_id,
            ticket_number=ticket.ticket_number,
            total_elapsed_ms=sum(t.elapsed_ms for t in stage_timings),
            stage_count=len(stage_timings),
        )
        return state
    finally:
        unsubscribe()
