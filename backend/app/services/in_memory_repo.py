"""In-memory twin of FirestoreRepo, same TicketRepository interface. Selected when ENV=local so
the whole pipeline (and every test) runs with zero GCP credentials.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.models import (
    Customer,
    PipelineState,
    Sender,
    Ticket,
    TicketDraft,
    TicketHistoryEntry,
    TicketStatus,
    Urgency,
)
from app.services.repository import TicketNotFoundError, TicketPage, decode_cursor, encode_cursor


def _customer_key(email: str | None, phone: str | None) -> str | None:
    """Customer identity convention: normalized email, else phone. See app/services/repository.py."""
    if email:
        return email.strip().lower()
    if phone:
        return phone.strip()
    return None


class InMemoryRepo:
    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._customers: dict[str, Customer] = {}
        self._pipeline_runs: dict[str, PipelineState] = {}
        self._counters: dict[str, int] = {}
        # asyncio is single-threaded/cooperative: without this lock, two concurrent create_ticket
        # calls could both read the same counter value before either writes it back, since await
        # points are the only place execution can interleave. One lock around every mutating method
        # closes that window - the same atomicity guarantee FirestoreRepo gets from a transaction,
        # via a different mechanism.
        self._lock = asyncio.Lock()

    @staticmethod
    def _ticket_key(vertical: str, ticket_number: str) -> str:
        return f"{vertical}__{ticket_number}"

    def _next_ticket_number_locked(self, vertical: str) -> str:
        next_value = self._counters.get(vertical, 0) + 1
        self._counters[vertical] = next_value
        return f"TK-{next_value:04d}"

    def _upsert_customer_locked(self, vertical: str, customer: Sender, now: datetime) -> None:
        key = _customer_key(customer.email, customer.phone)
        if key is None:
            return
        doc_id = f"{vertical}:{key}"
        existing = self._customers.get(doc_id)
        if existing is None:
            self._customers[doc_id] = Customer(
                customer_id=doc_id,
                vertical=vertical,
                name=customer.name,
                email=customer.email,
                phone=customer.phone,
                company=customer.company,
                first_seen_at=now,
                last_seen_at=now,
                ticket_count=1,
            )
        else:
            self._customers[doc_id] = existing.model_copy(
                update={
                    "last_seen_at": now,
                    "ticket_count": existing.ticket_count + 1,
                    "name": customer.name or existing.name,
                    "company": customer.company or existing.company,
                }
            )

    async def create_ticket(self, draft: TicketDraft) -> Ticket:
        async with self._lock:
            ticket_number = self._next_ticket_number_locked(draft.vertical)
            now = datetime.now(timezone.utc)
            ticket = Ticket(
                ticket_number=ticket_number,
                intake_id=draft.intake_id,
                vertical=draft.vertical,
                customer=draft.customer,
                issue_type=draft.issue_type,
                priority=draft.priority,
                status=draft.status,
                title=draft.title,
                description=draft.description,
                extracted_details=draft.extracted_details,
                missing_info=draft.missing_info,
                sentiment=draft.sentiment,
                confidence=draft.confidence,
                assigned_to=draft.assigned_to,
                created_at=now,
                updated_at=now,
                history=[TicketHistoryEntry(actor="system", action="ticket_created", timestamp=now)],
            )
            self._tickets[self._ticket_key(draft.vertical, ticket_number)] = ticket
            self._upsert_customer_locked(draft.vertical, draft.customer, now)
            return ticket

    async def get_ticket(self, ticket_number: str, *, vertical: str) -> Ticket | None:
        return self._tickets.get(self._ticket_key(vertical, ticket_number))

    async def _mutate_ticket_locked(
        self, ticket_number: str, *, vertical: str, entry: TicketHistoryEntry, new_status: TicketStatus | None
    ) -> Ticket:
        key = self._ticket_key(vertical, ticket_number)
        async with self._lock:
            ticket = self._tickets.get(key)
            if ticket is None:
                raise TicketNotFoundError(vertical, ticket_number)
            updates: dict = {
                "history": [*ticket.history, entry],
                "updated_at": datetime.now(timezone.utc),
            }
            if new_status is not None:
                updates["status"] = new_status
            updated = ticket.model_copy(update=updates)
            self._tickets[key] = updated
            return updated

    async def update_ticket_status(
        self,
        ticket_number: str,
        *,
        vertical: str,
        status: TicketStatus,
        actor: str,
        notes: str | None = None,
    ) -> Ticket:
        entry = TicketHistoryEntry(actor=actor, action=f"status_changed_to_{status.value}", notes=notes)
        return await self._mutate_ticket_locked(ticket_number, vertical=vertical, entry=entry, new_status=status)

    async def append_ticket_event(
        self, ticket_number: str, *, vertical: str, entry: TicketHistoryEntry
    ) -> Ticket:
        return await self._mutate_ticket_locked(ticket_number, vertical=vertical, entry=entry, new_status=None)

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
    ) -> TicketPage:
        candidates = [t for t in self._tickets.values() if t.vertical == vertical]
        if status is not None:
            candidates = [t for t in candidates if t.status == status]
        if priority is not None:
            candidates = [t for t in candidates if t.priority == priority]
        if category is not None:
            candidates = [t for t in candidates if t.issue_type == category]
        if search:
            needle = search.lower()
            candidates = [
                t for t in candidates if needle in t.title.lower() or needle in t.description.lower()
            ]

        candidates.sort(key=lambda t: (t.created_at, t.ticket_number), reverse=True)

        if cursor:
            cursor_created_at, cursor_ticket_number = decode_cursor(cursor)
            candidates = [
                t for t in candidates if (t.created_at, t.ticket_number) < (cursor_created_at, cursor_ticket_number)
            ]

        page_items = candidates[:limit]
        next_cursor = None
        if len(candidates) > limit:
            last = page_items[-1]
            next_cursor = encode_cursor(last.created_at, last.ticket_number)
        return TicketPage(items=page_items, next_cursor=next_cursor)

    async def find_customer_by_email_or_phone(
        self, *, vertical: str, email: str | None = None, phone: str | None = None
    ) -> Customer | None:
        key = _customer_key(email, phone)
        if key is None:
            raise ValueError("find_customer_by_email_or_phone requires email or phone")
        return self._customers.get(f"{vertical}:{key}")

    async def get_customer_history(
        self,
        *,
        vertical: str,
        email: str | None = None,
        phone: str | None = None,
        limit: int = 10,
    ) -> list[Ticket]:
        if not email and not phone:
            raise ValueError("get_customer_history requires email or phone")
        normalized_email = email.strip().lower() if email else None
        normalized_phone = phone.strip() if phone else None
        matches = [
            t
            for t in self._tickets.values()
            if t.vertical == vertical
            and (
                (normalized_email and t.customer.email and t.customer.email.strip().lower() == normalized_email)
                or (normalized_phone and t.customer.phone and t.customer.phone.strip() == normalized_phone)
            )
        ]
        matches.sort(key=lambda t: (t.created_at, t.ticket_number), reverse=True)
        return matches[:limit]

    async def save_pipeline_state(self, state: PipelineState) -> str:
        doc_id = state.message.intake_id
        async with self._lock:
            self._pipeline_runs[doc_id] = state
        return doc_id
