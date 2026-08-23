"""The output of the Ticket Agent."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field, ValidationInfo, field_validator

from app.models.base import TaskmasterModel
from app.models.common import Sender, validate_issue_type
from app.models.enums import Sentiment, TicketStatus, Urgency


class TicketHistoryEntry(TaskmasterModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str
    notes: str | None = None


class Ticket(TaskmasterModel):
    ticket_number: str
    intake_id: str
    vertical: str
    customer: Sender
    issue_type: str
    priority: Urgency
    status: TicketStatus
    title: str
    description: str
    extracted_details: dict[str, Any] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    assigned_to: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[TicketHistoryEntry] = Field(default_factory=list)

    @field_validator("issue_type")
    @classmethod
    def _validate_issue_type(cls, v: str, info: ValidationInfo) -> str:
        return validate_issue_type(v, info)


class TicketDraft(TaskmasterModel):
    """Everything needed to create a Ticket except the repo-assigned ticket_number, timestamps,
    and history. Passed to TicketRepository.create_ticket, which fills in the rest.
    """

    intake_id: str
    vertical: str
    customer: Sender
    issue_type: str
    priority: Urgency
    status: TicketStatus = TicketStatus.NEW
    title: str
    description: str
    extracted_details: dict[str, Any] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    assigned_to: str | None = None

    @field_validator("issue_type")
    @classmethod
    def _validate_issue_type(cls, v: str, info: ValidationInfo) -> str:
        return validate_issue_type(v, info)
