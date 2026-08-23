"""Repository tests, run entirely against InMemoryRepo (no GCP credentials needed)."""
from __future__ import annotations

import asyncio

import pytest

from app.models import Sender, Sentiment, TicketDraft, TicketHistoryEntry, TicketStatus, Urgency
from app.services.in_memory_repo import InMemoryRepo
from app.services.repository import TicketNotFoundError


def make_draft(
    *,
    vertical: str = "it_support",
    email: str | None = "jane@example.com",
    phone: str | None = None,
    title: str = "Printer unresponsive on 3rd floor",
    description: str = "The printer on the 3rd floor won't turn on.",
) -> TicketDraft:
    return TicketDraft(
        intake_id="intake-1",
        vertical=vertical,
        customer=Sender(name="Jane Doe", email=email, phone=phone),
        issue_type="hardware",
        priority=Urgency.HIGH,
        title=title,
        description=description,
        sentiment=Sentiment.ANNOYED,
        confidence=0.87,
    )


@pytest.fixture
def repo() -> InMemoryRepo:
    return InMemoryRepo()


# --- ticket numbering ---------------------------------------------------------


async def test_create_ticket_assigns_sequential_numbers_per_vertical(repo: InMemoryRepo):
    t1 = await repo.create_ticket(make_draft(vertical="it_support"))
    t2 = await repo.create_ticket(make_draft(vertical="it_support"))
    t3 = await repo.create_ticket(make_draft(vertical="dental_clinic"))

    assert t1.ticket_number == "TK-0001"
    assert t2.ticket_number == "TK-0002"
    assert t3.ticket_number == "TK-0001"  # independent sequence for a different vertical


async def test_concurrent_create_ticket_no_duplicate_numbers(repo: InMemoryRepo):
    results = await asyncio.gather(*[repo.create_ticket(make_draft()) for _ in range(10)])
    numbers = [t.ticket_number for t in results]
    assert len(set(numbers)) == 10


# --- get / mutate --------------------------------------------------------------


async def test_get_ticket_roundtrip(repo: InMemoryRepo):
    created = await repo.create_ticket(make_draft())
    fetched = await repo.get_ticket(created.ticket_number, vertical="it_support")
    assert fetched == created


async def test_get_ticket_missing_returns_none(repo: InMemoryRepo):
    assert await repo.get_ticket("TK-9999", vertical="it_support") is None


async def test_update_ticket_status_appends_history_and_updates_status(repo: InMemoryRepo):
    created = await repo.create_ticket(make_draft())
    updated = await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=TicketStatus.IN_PROGRESS, actor="tech-1"
    )
    assert updated.status == TicketStatus.IN_PROGRESS
    assert len(updated.history) == len(created.history) + 1
    assert updated.history[-1].actor == "tech-1"
    assert updated.updated_at >= created.updated_at


async def test_update_ticket_status_missing_ticket_raises_not_found(repo: InMemoryRepo):
    with pytest.raises(TicketNotFoundError):
        await repo.update_ticket_status(
            "TK-9999", vertical="it_support", status=TicketStatus.RESOLVED, actor="tech-1"
        )


async def test_append_ticket_event(repo: InMemoryRepo):
    created = await repo.create_ticket(make_draft())
    entry = TicketHistoryEntry(actor="tech-1", action="called_customer", notes="left voicemail")
    updated = await repo.append_ticket_event(created.ticket_number, vertical="it_support", entry=entry)
    assert updated.history[-1] == entry
    assert updated.status == created.status  # unaffected


# --- list_tickets ---------------------------------------------------------------


async def test_list_tickets_filters_by_status_priority_category(repo: InMemoryRepo):
    t1 = await repo.create_ticket(make_draft(title="Network down"))
    await repo.update_ticket_status(t1.ticket_number, vertical="it_support", status=TicketStatus.RESOLVED, actor="x")
    await repo.create_ticket(make_draft(title="Laptop broken"))

    page = await repo.list_tickets(vertical="it_support", status=TicketStatus.RESOLVED)
    assert [t.ticket_number for t in page.items] == [t1.ticket_number]

    page = await repo.list_tickets(vertical="it_support", priority=Urgency.HIGH)
    assert len(page.items) == 2

    page = await repo.list_tickets(vertical="it_support", category="hardware")
    assert len(page.items) == 2

    page = await repo.list_tickets(vertical="it_support", category="software")
    assert page.items == []


async def test_list_tickets_pagination_cursor_no_overlap_or_skip(repo: InMemoryRepo):
    created = [await repo.create_ticket(make_draft(title=f"issue {i}")) for i in range(5)]
    expected_order = sorted((t.ticket_number for t in created), reverse=True)

    page1 = await repo.list_tickets(vertical="it_support", limit=2)
    assert [t.ticket_number for t in page1.items] == expected_order[:2]
    assert page1.next_cursor is not None

    page2 = await repo.list_tickets(vertical="it_support", limit=2, cursor=page1.next_cursor)
    assert [t.ticket_number for t in page2.items] == expected_order[2:4]
    assert page2.next_cursor is not None

    page3 = await repo.list_tickets(vertical="it_support", limit=2, cursor=page2.next_cursor)
    assert [t.ticket_number for t in page3.items] == expected_order[4:5]
    assert page3.next_cursor is None


async def test_list_tickets_search_matches_title_or_description(repo: InMemoryRepo):
    await repo.create_ticket(make_draft(title="VPN is down", description="cannot connect from home"))
    await repo.create_ticket(make_draft(title="Laptop broken", description="screen is cracked"))

    page = await repo.list_tickets(vertical="it_support", search="vpn")
    assert len(page.items) == 1
    assert "VPN" in page.items[0].title

    page = await repo.list_tickets(vertical="it_support", search="cracked")
    assert len(page.items) == 1
    assert "Laptop" in page.items[0].title


# --- customers -------------------------------------------------------------------


async def test_create_ticket_upserts_customer_and_increments_ticket_count(repo: InMemoryRepo):
    await repo.create_ticket(make_draft(email="jane@example.com"))
    await repo.create_ticket(make_draft(email="jane@example.com"))

    customer = await repo.find_customer_by_email_or_phone(vertical="it_support", email="jane@example.com")
    assert customer is not None
    assert customer.ticket_count == 2


async def test_find_customer_requires_email_or_phone(repo: InMemoryRepo):
    with pytest.raises(ValueError):
        await repo.find_customer_by_email_or_phone(vertical="it_support")


async def test_get_customer_history_returns_tickets_for_that_customer(repo: InMemoryRepo):
    mine = await repo.create_ticket(make_draft(email="jane@example.com", title="ticket A"))
    await repo.create_ticket(make_draft(email="someone.else@example.com", title="ticket B"))
    mine2 = await repo.create_ticket(make_draft(email="jane@example.com", title="ticket C"))

    history = await repo.get_customer_history(vertical="it_support", email="jane@example.com")
    assert {t.ticket_number for t in history} == {mine.ticket_number, mine2.ticket_number}


# --- pipeline state ---------------------------------------------------------------


async def test_save_pipeline_state_does_not_raise_and_returns_intake_id(repo: InMemoryRepo):
    from app.models import Channel, NormalizedMessage, PipelineState

    state = PipelineState(
        message=NormalizedMessage(
            intake_id="intake-42",
            vertical="it_support",
            channel=Channel.EMAIL,
            sender=Sender(email="jane@example.com"),
            body_text="hello",
        )
    )
    doc_id = await repo.save_pipeline_state(state)
    assert doc_id == "intake-42"
