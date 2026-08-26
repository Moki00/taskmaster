"""Firestore repository behavior tests using mocked SDK responses."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.models import Sender, Sentiment, Ticket, TicketStatus, Urgency
from app.services.firestore_repo import FirestoreRepo


class FakeDocumentSnapshot:
    def __init__(self, ticket: Ticket | None = None, *, exists: bool = True) -> None:
        self._ticket = ticket
        self.exists = exists

    def to_dict(self) -> dict:
        assert self._ticket is not None
        return self._ticket.model_dump(mode="json")


async def _async_iter(items: list[FakeDocumentSnapshot]):
    for item in items:
        yield item


def make_ticket(ticket_number: str, created_at: datetime) -> Ticket:
    return Ticket(
        ticket_number=ticket_number,
        intake_id=f"intake-{ticket_number}",
        vertical="it_support",
        customer=Sender(name="Jane Doe", email="jane@example.com"),
        issue_type="hardware",
        priority=Urgency.HIGH,
        status=TicketStatus.OPEN,
        title=f"Issue {ticket_number}",
        description="The printer is unavailable.",
        sentiment=Sentiment.ANNOYED,
        confidence=0.9,
        created_at=created_at,
        updated_at=created_at,
    )


async def test_firestore_get_ticket_returns_none_when_document_is_missing():
    """A missing vertical-scoped Firestore document maps to None."""
    repo = object.__new__(FirestoreRepo)
    collection = MagicMock()
    collection.document.return_value.get = AsyncMock(
        return_value=FakeDocumentSnapshot(exists=False)
    )
    repo._tickets_col = MagicMock(return_value=collection)

    result = await repo.get_ticket("TK-0001", vertical="it_support")

    assert result is None
    collection.document.assert_called_once_with("it_support__TK-0001")


async def test_firestore_get_ticket_deserializes_existing_document():
    """An existing document is returned as the shared Ticket model."""
    repo = object.__new__(FirestoreRepo)
    expected = make_ticket("TK-0001", datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc))
    collection = MagicMock()
    collection.document.return_value.get = AsyncMock(
        return_value=FakeDocumentSnapshot(expected)
    )
    repo._tickets_col = MagicMock(return_value=collection)

    result = await repo.get_ticket("TK-0001", vertical="it_support")

    assert result == expected
    assert isinstance(result, Ticket)
    collection.document.assert_called_once_with("it_support__TK-0001")


async def test_firestore_list_tickets_exact_final_page_has_no_cursor():
    """A final page exactly at the limit must not advertise an empty next page."""
    repo = object.__new__(FirestoreRepo)
    first = make_ticket("TK-0002", datetime(2026, 8, 25, 10, 1, tzinfo=timezone.utc))
    second = make_ticket("TK-0001", datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc))

    query = MagicMock()
    query.limit.return_value.stream.return_value = _async_iter(
        [FakeDocumentSnapshot(first), FakeDocumentSnapshot(second)]
    )
    repo._base_query = MagicMock(return_value=query)

    page = await repo.list_tickets(vertical="it_support", limit=2)

    assert [ticket.ticket_number for ticket in page.items] == ["TK-0002", "TK-0001"]
    assert page.next_cursor is None
    query.limit.assert_called_once_with(3)


async def test_firestore_list_tickets_returns_cursor_when_an_extra_item_exists():
    """An extra fetched document proves that another page exists."""
    repo = object.__new__(FirestoreRepo)
    tickets = [
        make_ticket("TK-0003", datetime(2026, 8, 25, 10, 2, tzinfo=timezone.utc)),
        make_ticket("TK-0002", datetime(2026, 8, 25, 10, 1, tzinfo=timezone.utc)),
        make_ticket("TK-0001", datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)),
    ]

    query = MagicMock()
    query.limit.return_value.stream.return_value = _async_iter(
        [FakeDocumentSnapshot(ticket) for ticket in tickets]
    )
    repo._base_query = MagicMock(return_value=query)

    page = await repo.list_tickets(vertical="it_support", limit=2)

    assert [ticket.ticket_number for ticket in page.items] == ["TK-0003", "TK-0002"]
    assert page.next_cursor is not None
    query.limit.assert_called_once_with(3)
