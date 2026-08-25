"""The output of the Scheduler Agent."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field, model_validator

from app.models.base import TaskmasterModel
from app.models.enums import AppointmentStatus


class TimeSlot(TaskmasterModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _check_ordering(self) -> "TimeSlot":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class Appointment(TaskmasterModel):
    appointment_id: str
    ticket_number: str
    vertical: str
    appointment_type: str
    assignee: str | None = None
    proposed_slots: list[TimeSlot] = Field(default_factory=list)
    confirmed_slot: TimeSlot | None = None
    calendar_event_id: str | None = None
    status: AppointmentStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
