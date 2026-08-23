"""Pydantic v2 contract shared between all 5 agents. Import from here, not submodules."""
from app.models.appointment import Appointment, TimeSlot
from app.models.classification import Classification
from app.models.common import Attachment, Sender
from app.models.customer import Customer
from app.models.enums import (
    AppointmentStatus,
    Channel,
    Sentiment,
    TicketStatus,
    Urgency,
)
from app.models.message import NormalizedMessage
from app.models.pipeline import (
    PipelineErrorEntry,
    PipelineEvent,
    PipelineState,
    StageTiming,
)
from app.models.reply import ReplyDraft
from app.models.ticket import Ticket, TicketDraft, TicketHistoryEntry

__all__ = [
    "Appointment",
    "AppointmentStatus",
    "Attachment",
    "Channel",
    "Classification",
    "Customer",
    "NormalizedMessage",
    "PipelineErrorEntry",
    "PipelineEvent",
    "PipelineState",
    "ReplyDraft",
    "Sender",
    "Sentiment",
    "StageTiming",
    "Ticket",
    "TicketDraft",
    "TicketHistoryEntry",
    "TicketStatus",
    "TimeSlot",
    "Urgency",
]
