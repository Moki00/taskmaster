"""PipelineState: the full state threaded through Intake -> Classifier -> Ticket -> Reply -> Scheduler."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from app.models.appointment import Appointment
from app.models.base import TaskmasterModel
from app.models.classification import Classification
from app.models.message import NormalizedMessage
from app.models.reply import ReplyDraft
from app.models.ticket import Ticket


class StageTiming(TaskmasterModel):
    stage: str
    elapsed_ms: float = Field(ge=0.0)
    correlation_id: str


class PipelineEvent(TaskmasterModel):
    event: str
    stage: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)


class PipelineErrorEntry(TaskmasterModel):
    stage: str
    message: str
    error_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineState(TaskmasterModel):
    message: NormalizedMessage
    classification: Classification | None = None
    ticket: Ticket | None = None
    reply: ReplyDraft | None = None
    appointment: Appointment | None = None
    stage_timings: list[StageTiming] = Field(default_factory=list)
    events: list[PipelineEvent] = Field(default_factory=list)
    errors: list[PipelineErrorEntry] = Field(default_factory=list)
