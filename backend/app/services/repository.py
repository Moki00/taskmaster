"""The ticket/customer/pipeline-run persistence contract. Agents depend on TicketRepository and
get_repository() only — never on FirestoreRepo or InMemoryRepo directly, and never touch the
Firestore SDK.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.config import settings
from app.models import Customer, PipelineState, Ticket, TicketDraft, TicketHistoryEntry, TicketStatus, Urgency
from app.models.base import TaskmasterModel


class RepoError(Exception):
    """Base for all repository errors."""


class TicketNotFoundError(RepoError):
    def __init__(self, vertical: str, ticket_number: str) -> None:
        super().__init__(f"No ticket '{ticket_number}' found for vertical '{vertical}'")
        self.vertical = vertical
        self.ticket_number = ticket_number


class TicketPage(TaskmasterModel):
    items: list[Ticket]
    next_cursor: str | None = None


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
    ) -> Ticket: ...

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
