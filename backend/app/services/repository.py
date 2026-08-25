"""The ticket/customer/pipeline-run persistence contract. Agents depend on TicketRepository and
get_repository() only — never on FirestoreRepo or InMemoryRepo directly, and never touch the
Firestore SDK.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.config import settings
from app.models import (
    Appointment,
    AppointmentStatus,
    Customer,
    PipelineState,
    Ticket,
    TicketDraft,
    TicketHistoryEntry,
    TicketStatus,
    Urgency,
)
from app.models.base import TaskmasterModel

# How many days back a prior ticket from the same customer, about the same issue_type, still
# counts as "contacting us again" for repeat-contact detection (see create_ticket).
REPEAT_CONTACT_WINDOW_DAYS = 7
# Cap on how many prior tickets we surface on related_ticket_numbers - informational, not
# exhaustive.
REPEAT_CONTACT_LOOKBACK_LIMIT = 5


class RepoError(Exception):
    """Base for all repository errors."""


class TicketNotFoundError(RepoError):
    def __init__(self, vertical: str, ticket_number: str) -> None:
        super().__init__(f"No ticket '{ticket_number}' found for vertical '{vertical}'")
        self.vertical = vertical
        self.ticket_number = ticket_number


class InvalidStatusTransitionError(RepoError):
    def __init__(self, current: TicketStatus, new: TicketStatus) -> None:
        super().__init__(f"cannot move ticket from {current.value} to {new.value}")
        self.current = current
        self.new = new


class TicketPage(TaskmasterModel):
    items: list[Ticket]
    next_cursor: str | None = None


# The valid ticket lifecycle: forward-or-stay along this chain, skipping ahead is fine (not every
# ticket needs every state), never backward. NEEDS_REVIEW is the universal escape hatch - reachable
# from and to every state, chain position doesn't apply to it.
_STATUS_CHAIN = [
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.SCHEDULED,
    TicketStatus.RESOLVED,
    TicketStatus.CLOSED,
]
_STATUS_CHAIN_INDEX = {status: i for i, status in enumerate(_STATUS_CHAIN)}


def validate_status_transition(current: TicketStatus, new: TicketStatus) -> None:
    """Raises InvalidStatusTransitionError for a backward jump along the chain. Same-status is a
    no-op. NEEDS_REVIEW is reachable from, and can move to, every other status.
    """
    if current == new or current == TicketStatus.NEEDS_REVIEW or new == TicketStatus.NEEDS_REVIEW:
        return
    if _STATUS_CHAIN_INDEX[new] < _STATUS_CHAIN_INDEX[current]:
        raise InvalidStatusTransitionError(current, new)


def encode_cursor(created_at: datetime, ticket_number: str) -> str:
    """Opaque pagination cursor. Same format for both repo implementations."""
    return f"{created_at.isoformat()}::{ticket_number}"


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    created_at_str, _, ticket_number = cursor.partition("::")
    return datetime.fromisoformat(created_at_str), ticket_number


class TicketRepository(Protocol):
    async def create_ticket(self, draft: TicketDraft) -> Ticket: ...

    async def get_ticket(self, ticket_number: str, *, vertical: str) -> Ticket | None: ...

    async def update_ticket_status(
        self,
        ticket_number: str,
        *,
        vertical: str,
        status: TicketStatus,
        actor: str,
        notes: str | None = None,
        agent_name: str | None = None,
        correlation_id: str | None = None,
    ) -> Ticket:
        """Raises InvalidStatusTransitionError if `status` is not reachable from the ticket's
        current status (see validate_status_transition), TicketNotFoundError if the ticket
        doesn't exist. Never writes on an invalid transition.
        """
        ...

    async def list_tickets(
        self,
        *,
        vertical: str,
        status: TicketStatus | None = None,
        priority: Urgency | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> TicketPage: ...

    async def find_customer_by_email_or_phone(
        self, *, vertical: str, email: str | None = None, phone: str | None = None
    ) -> Customer | None: ...

    async def get_customer_history(
        self,
        *,
        vertical: str,
        email: str | None = None,
        phone: str | None = None,
        limit: int = 10,
    ) -> list[Ticket]: ...

    async def append_ticket_event(
        self, ticket_number: str, *, vertical: str, entry: TicketHistoryEntry
    ) -> Ticket: ...

    async def save_pipeline_state(self, state: PipelineState) -> str: ...

    async def save_appointment(self, appointment: Appointment) -> str: ...

    async def get_appointment(self, appointment_id: str, *, vertical: str) -> Appointment | None: ...

    async def list_appointments_for_ticket(
        self, ticket_number: str, *, vertical: str
    ) -> list[Appointment]: ...

    async def list_appointments(
        self,
        vertical: str,
        *,
        from_date: datetime,
        to_date: datetime,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        """Filters on confirmed_slot.start within [from_date, to_date]. Appointments with no
        confirmed_slot (still only proposed) are excluded - there's no single date to range
        against yet.
        """
        ...

    async def check_and_mark(self, provider_message_id: str, *, vertical: str) -> bool:
        """Idempotency guard for webhook ingestion. Returns True the first time a given
        provider_message_id is seen (not a duplicate - proceed with creating a ticket), and False
        on every subsequent call with the same id (already processed - skip it). Safe under
        concurrent/retried delivery of the same webhook.
        """
        ...


_repo_instance: TicketRepository | None = None


def get_repository() -> TicketRepository:
    """Process-wide repo singleton. InMemoryRepo for ENV=local, FirestoreRepo otherwise.

    The FirestoreRepo import happens inside this branch so that importing this module (or running
    with ENV=local) never requires google-cloud-firestore credentials to be available.
    """
    global _repo_instance
    if _repo_instance is None:
        if settings.ENV == "local":
            from app.services.in_memory_repo import InMemoryRepo

            _repo_instance = InMemoryRepo()
        else:
            from app.services.firestore_repo import FirestoreRepo

            _repo_instance = FirestoreRepo()
    return _repo_instance
