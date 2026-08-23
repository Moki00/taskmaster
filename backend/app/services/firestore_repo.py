"""Firestore-backed TicketRepository. Selected by get_repository() when ENV != "local".

Required composite indexes (Firestore raises FailedPrecondition with an auto-create link at query
time if these are missing; this is the reference list for firestore.indexes.json):

    tickets: (vertical ASC, created_at DESC, ticket_number DESC)               -- base list_tickets query
    tickets: (vertical ASC, status ASC, created_at DESC, ticket_number DESC)
    tickets: (vertical ASC, priority ASC, created_at DESC, ticket_number DESC)
    tickets: (vertical ASC, issue_type ASC, created_at DESC, ticket_number DESC)
    -- combining two or more optional filters at once (e.g. status + priority) needs one more
    -- composite index per combination in use; add as Firestore's error links prompt.
    -- `search` is filtered client-side (Firestore has no native full-text search), so it needs no
    -- index of its own.

Collections (all prefixed by settings.FIRESTORE_COLLECTION_PREFIX): "{prefix}_tickets",
"{prefix}_customers", "{prefix}_pipeline_runs", "{prefix}_counters".
"""
from __future__ import annotations

from datetime import datetime, timezone

from google.cloud import firestore

from app.config import settings
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

MAX_SEARCH_SCAN = 500


def _customer_key(email: str | None, phone: str | None) -> str | None:
    """Customer identity convention: normalized email, else phone. Mirrors in_memory_repo.py."""
    if email:
        return email.strip().lower()
    if phone:
        return phone.strip()
    return None


class FirestoreRepo:
    def __init__(self) -> None:
        self._db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID)
        self._prefix = settings.FIRESTORE_COLLECTION_PREFIX

    def _tickets_col(self):
        return self._db.collection(f"{self._prefix}_tickets")

    def _customers_col(self):
        return self._db.collection(f"{self._prefix}_customers")

    def _pipeline_runs_col(self):
        return self._db.collection(f"{self._prefix}_pipeline_runs")

    def _counters_col(self):
        return self._db.collection(f"{self._prefix}_counters")

    @staticmethod
    def _ticket_doc_id(vertical: str, ticket_number: str) -> str:
        # Required, not just convenient: ticket numbers are only unique per vertical (see plan /
        # GEMINI.md), so the vertical must be baked into the document id.
        return f"{vertical}__{ticket_number}"

    async def _next_ticket_number(self, vertical: str) -> str:
        """Reads+increments {prefix}_counters/{vertical} inside a Firestore transaction.

        Safety: Firestore transactions are optimistic. If another concurrent transaction touches
        this same counter document between this read and this write, Firestore aborts it and the
        client library automatically retries the whole transaction function. That makes this
        read-increment-write atomic under many simultaneous create_ticket calls with no explicit
        locking required.
        """
        counter_ref = self._counters_col().document(vertical)
        transaction = self._db.transaction()

        @firestore.async_transactional
        async def _increment(transaction: firestore.AsyncTransaction) -> int:
            snapshot = None
            async for s in transaction.get(counter_ref):
                snapshot = s
            current = snapshot.get("value") if snapshot is not None and snapshot.exists else 0
            next_value = current + 1
            transaction.set(counter_ref, {"value": next_value})
            return next_value

        next_value = await _increment(transaction)
        return f"TK-{next_value:04d}"

    def _upsert_customer(self, transaction: firestore.AsyncTransaction, vertical: str, customer: Sender, now: datetime) -> None:
        key = _customer_key(customer.email, customer.phone)
        if key is None:
            return
        doc_ref = self._customers_col().document(f"{vertical}:{key}")
        # Staged as part of the caller's transaction/batch context by the caller.
        transaction.set(
            doc_ref,
            {
                "customer_id": f"{vertical}:{key}",
                "vertical": vertical,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "company": customer.company,
                "last_seen_at": now.isoformat(),
                "first_seen_at": firestore.SERVER_TIMESTAMP,
                "ticket_count": firestore.Increment(1),
            },
            merge=True,
        )

    async def create_ticket(self, draft: TicketDraft) -> Ticket:
        ticket_number = await self._next_ticket_number(draft.vertical)
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
        doc_ref = self._tickets_col().document(self._ticket_doc_id(draft.vertical, ticket_number))
        await doc_ref.set(ticket.model_dump(mode="json"))

        # Kept as a separate transaction from the ticket write for simplicity - a stricter system
        # would combine both into one transaction. Skipped entirely if the customer has neither
        # email nor phone to key on.
        if _customer_key(draft.customer.email, draft.customer.phone) is not None:
            customer_transaction = self._db.transaction()

            @firestore.async_transactional
            async def _upsert(transaction: firestore.AsyncTransaction) -> None:
                self._upsert_customer(transaction, draft.vertical, draft.customer, now)

            await _upsert(customer_transaction)

        return ticket

    async def get_ticket(self, ticket_number: str, *, vertical: str) -> Ticket | None:
        snapshot = await self._tickets_col().document(self._ticket_doc_id(vertical, ticket_number)).get()
        if not snapshot.exists:
            return None
        return Ticket.model_validate(snapshot.to_dict())

    async def _mutate_ticket(
        self, ticket_number: str, *, vertical: str, entry: TicketHistoryEntry, new_status: TicketStatus | None
    ) -> Ticket:
        doc_ref = self._tickets_col().document(self._ticket_doc_id(vertical, ticket_number))
        transaction = self._db.transaction()

        @firestore.async_transactional
        async def _apply(transaction: firestore.AsyncTransaction) -> Ticket:
            snapshot = None
            async for s in transaction.get(doc_ref):
                snapshot = s
            if snapshot is None or not snapshot.exists:
                raise TicketNotFoundError(vertical, ticket_number)
            ticket = Ticket.model_validate(snapshot.to_dict())
            updates: dict = {
                "history": [*ticket.history, entry],
                "updated_at": datetime.now(timezone.utc),
            }
            if new_status is not None:
                updates["status"] = new_status
            updated = ticket.model_copy(update=updates)
            transaction.set(doc_ref, updated.model_dump(mode="json"))
            return updated

        return await _apply(transaction)

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
        return await self._mutate_ticket(ticket_number, vertical=vertical, entry=entry, new_status=status)

    async def append_ticket_event(
        self, ticket_number: str, *, vertical: str, entry: TicketHistoryEntry
    ) -> Ticket:
        return await self._mutate_ticket(ticket_number, vertical=vertical, entry=entry, new_status=None)

    def _base_query(
        self,
        *,
        vertical: str,
        status: TicketStatus | None,
        priority: Urgency | None,
        category: str | None,
    ):
        query = self._tickets_col().where("vertical", "==", vertical)
        if status is not None:
            query = query.where("status", "==", status.value)
        if priority is not None:
            query = query.where("priority", "==", priority.value)
        if category is not None:
            query = query.where("issue_type", "==", category)
        return query.order_by("created_at", direction=firestore.Query.DESCENDING).order_by(
            "ticket_number", direction=firestore.Query.DESCENDING
        )

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
        query = self._base_query(vertical=vertical, status=status, priority=priority, category=category)

        if cursor:
            cursor_created_at, cursor_ticket_number = decode_cursor(cursor)
            query = query.start_after({"created_at": cursor_created_at.isoformat(), "ticket_number": cursor_ticket_number})

        if not search:
            docs = [Ticket.model_validate(d.to_dict()) async for d in query.limit(limit).stream()]
            next_cursor = (
                encode_cursor(docs[-1].created_at, docs[-1].ticket_number) if len(docs) == limit else None
            )
            return TicketPage(items=docs, next_cursor=next_cursor)

        # Firestore has no native full-text search. Scan a bounded window and filter client-side.
        # The cursor always advances to the last SCANNED doc (not the last MATCHED one), so paging
        # never skips a document - a page may return fewer than `limit` matches; a non-null
        # next_cursor just means "keep scanning." A real search index (Algolia/Typesense/Cloud
        # Search) should replace this before result volume makes the scan expensive.
        needle = search.lower()
        scanned = [d async for d in query.limit(MAX_SEARCH_SCAN).stream()]
        scanned_tickets = [Ticket.model_validate(d.to_dict()) for d in scanned]
        matches = [
            t for t in scanned_tickets if needle in t.title.lower() or needle in t.description.lower()
        ][:limit]
        next_cursor = None
        if len(scanned_tickets) == MAX_SEARCH_SCAN:
            last = scanned_tickets[-1]
            next_cursor = encode_cursor(last.created_at, last.ticket_number)
        return TicketPage(items=matches, next_cursor=next_cursor)

    async def find_customer_by_email_or_phone(
        self, *, vertical: str, email: str | None = None, phone: str | None = None
    ) -> Customer | None:
        key = _customer_key(email, phone)
        if key is None:
            raise ValueError("find_customer_by_email_or_phone requires email or phone")
        snapshot = await self._customers_col().document(f"{vertical}:{key}").get()
        if not snapshot.exists:
            return None
        return Customer.model_validate(snapshot.to_dict())

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

        # No customer_id FK on Ticket, so this queries tickets directly rather than joining
        # through the customers collection.
        field, value = ("customer.email", email.strip().lower()) if email else ("customer.phone", phone.strip())
        query = (
            self._tickets_col()
            .where("vertical", "==", vertical)
            .where(field, "==", value)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [Ticket.model_validate(d.to_dict()) async for d in query.stream()]

    async def save_pipeline_state(self, state: PipelineState) -> str:
        doc_id = state.message.intake_id
        payload = state.model_dump(mode="json")
        payload["vertical"] = state.message.vertical
        await self._pipeline_runs_col().document(doc_id).set(payload)
        return doc_id
