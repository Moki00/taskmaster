"""Repository tests, run entirely against InMemoryRepo (no GCP credentials needed)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Appointment,
    AppointmentStatus,
    Sender,
    Sentiment,
    TicketDraft,
    TicketHistoryEntry,
    TicketStatus,
    TimeSlot,
    Urgency,
)
from app.services.in_memory_repo import InMemoryRepo
from app.services.repository import InvalidStatusTransitionError, TicketNotFoundError


def make_draft(
    *,
    vertical: str = "it_support",
    email: str | None = "jane@example.com",
    phone: str | None = None,
    title: str = "Printer unresponsive on 3rd floor",
    description: str = "The printer on the 3rd floor won't turn on.",
    issue_type: str = "hardware",
) -> TicketDraft:
    return TicketDraft(
        intake_id="intake-1",
        vertical=vertical,
        customer=Sender(name="Jane Doe", email=email, phone=phone),
        issue_type=issue_type,
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


# --- status transitions ---------------------------------------------------------


@pytest.mark.parametrize(
    "to_status",
    [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.SCHEDULED,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ],
)
async def test_valid_forward_or_stay_transitions_succeed(repo: InMemoryRepo, to_status: TicketStatus):
    created = await repo.create_ticket(make_draft())  # starts OPEN
    updated = await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=to_status, actor="tech-1"
    )
    assert updated.status == to_status


@pytest.mark.parametrize(
    "current,invalid_target",
    [
        (TicketStatus.CLOSED, TicketStatus.OPEN),
        (TicketStatus.RESOLVED, TicketStatus.IN_PROGRESS),
        (TicketStatus.SCHEDULED, TicketStatus.OPEN),
    ],
)
async def test_backward_transitions_are_rejected(
    repo: InMemoryRepo, current: TicketStatus, invalid_target: TicketStatus
):
    created = await repo.create_ticket(make_draft())
    await repo.update_ticket_status(created.ticket_number, vertical="it_support", status=current, actor="x")
    with pytest.raises(InvalidStatusTransitionError):
        await repo.update_ticket_status(
            created.ticket_number, vertical="it_support", status=invalid_target, actor="x"
        )


@pytest.mark.parametrize(
    "chain_status",
    [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.SCHEDULED,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ],
)
async def test_needs_review_reachable_from_every_status(repo: InMemoryRepo, chain_status: TicketStatus):
    created = await repo.create_ticket(make_draft())
    await repo.update_ticket_status(created.ticket_number, vertical="it_support", status=chain_status, actor="x")
    updated = await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=TicketStatus.NEEDS_REVIEW, actor="x"
    )
    assert updated.status == TicketStatus.NEEDS_REVIEW


@pytest.mark.parametrize(
    "chain_status",
    [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.SCHEDULED,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ],
)
async def test_needs_review_can_transition_to_every_status(repo: InMemoryRepo, chain_status: TicketStatus):
    created = await repo.create_ticket(make_draft())
    await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=TicketStatus.NEEDS_REVIEW, actor="x"
    )
    updated = await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=chain_status, actor="x"
    )
    assert updated.status == chain_status


# --- audit trail -------------------------------------------------------------------


async def test_update_ticket_status_records_agent_name_and_correlation_id(repo: InMemoryRepo):
    created = await repo.create_ticket(make_draft())
    updated = await repo.update_ticket_status(
        created.ticket_number,
        vertical="it_support",
        status=TicketStatus.IN_PROGRESS,
        actor="classifier_agent",
        agent_name="classifier_agent",
        correlation_id="intake-1",
    )
    entry = updated.history[-1]
    assert entry.agent_name == "classifier_agent"
    assert entry.correlation_id == "intake-1"


async def test_history_entries_are_never_mutated_by_later_writes(repo: InMemoryRepo):
    created = await repo.create_ticket(make_draft())
    after_first = await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=TicketStatus.IN_PROGRESS, actor="a"
    )
    snapshot = list(after_first.history)

    await repo.update_ticket_status(
        created.ticket_number, vertical="it_support", status=TicketStatus.SCHEDULED, actor="b"
    )
    await repo.append_ticket_event(
        created.ticket_number,
        vertical="it_support",
        entry=TicketHistoryEntry(actor="c", action="note_added"),
    )

    final = await repo.get_ticket(created.ticket_number, vertical="it_support")
    assert final is not None
    assert final.history[: len(snapshot)] == snapshot


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


# --- repeat customer detection ----------------------------------------------------


async def test_repeat_contact_flagged_within_window_same_issue_type(repo: InMemoryRepo):
    first = await repo.create_ticket(make_draft(email="jane@example.com", issue_type="hardware"))
    second = await repo.create_ticket(make_draft(email="jane@example.com", issue_type="hardware"))

    assert second.is_repeat_issue is True
    assert first.ticket_number in second.related_ticket_numbers


async def test_repeat_contact_not_flagged_for_different_issue_type(repo: InMemoryRepo):
    await repo.create_ticket(make_draft(email="jane@example.com", issue_type="hardware"))
    second = await repo.create_ticket(make_draft(email="jane@example.com", issue_type="network"))

    assert second.is_repeat_issue is False
    assert second.related_ticket_numbers == []


async def test_repeat_contact_not_flagged_for_different_customer(repo: InMemoryRepo):
    await repo.create_ticket(make_draft(email="jane@example.com", issue_type="hardware"))
    other = await repo.create_ticket(make_draft(email="other@example.com", issue_type="hardware"))

    assert other.is_repeat_issue is False


async def test_repeat_contact_not_flagged_when_prior_ticket_older_than_window(repo: InMemoryRepo):
    first = await repo.create_ticket(make_draft(email="jane@example.com", issue_type="hardware"))
    key = repo._compound_key("it_support", first.ticket_number)
    repo._tickets[key] = repo._tickets[key].model_copy(
        update={"created_at": datetime.now(timezone.utc) - timedelta(days=8)}
    )

    second = await repo.create_ticket(make_draft(email="jane@example.com", issue_type="hardware"))
    assert second.is_repeat_issue is False


# --- idempotency ---------------------------------------------------------------


async def test_check_and_mark_true_then_false_for_same_id(repo: InMemoryRepo):
    assert await repo.check_and_mark("msg-1", vertical="it_support") is True
    assert await repo.check_and_mark("msg-1", vertical="it_support") is False


async def test_check_and_mark_true_for_different_ids(repo: InMemoryRepo):
    assert await repo.check_and_mark("msg-1", vertical="it_support") is True
    assert await repo.check_and_mark("msg-2", vertical="it_support") is True


async def test_check_and_mark_concurrent_same_id_exactly_one_true(repo: InMemoryRepo):
    results = await asyncio.gather(
        *[repo.check_and_mark("msg-dup", vertical="it_support") for _ in range(10)]
    )
    assert results.count(True) == 1
    assert results.count(False) == 9


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


# --- appointments ------------------------------------------------------------------


def make_appointment(*, vertical: str = "it_support", appointment_id: str = "appt-1") -> Appointment:
    return Appointment(
        appointment_id=appointment_id,
        ticket_number="TK-0001",
        vertical=vertical,
        appointment_type="onsite_visit",
        assignee="tech-1",
        status=AppointmentStatus.PROPOSED,
    )


async def test_save_appointment_does_not_raise_and_returns_appointment_id(repo: InMemoryRepo):
    appointment_id = await repo.save_appointment(make_appointment())
    assert appointment_id == "appt-1"


async def test_save_appointment_is_scoped_by_vertical(repo: InMemoryRepo):
    await repo.save_appointment(make_appointment(vertical="it_support", appointment_id="appt-1"))
    await repo.save_appointment(make_appointment(vertical="dental_clinic", appointment_id="appt-1"))

    assert repo._appointments["it_support__appt-1"].vertical == "it_support"
    assert repo._appointments["dental_clinic__appt-1"].vertical == "dental_clinic"
    assert len(repo._appointments) == 2


# --- appointment reads ---------------------------------------------------------


async def test_get_appointment_found_and_missing(repo: InMemoryRepo):
    await repo.save_appointment(make_appointment(appointment_id="appt-1"))

    found = await repo.get_appointment("appt-1", vertical="it_support")
    assert found is not None
    assert found.appointment_id == "appt-1"

    assert await repo.get_appointment("appt-does-not-exist", vertical="it_support") is None


async def test_list_appointments_for_ticket_scoped_correctly(repo: InMemoryRepo):
    await repo.save_appointment(make_appointment(appointment_id="a1"))  # ticket_number TK-0001
    await repo.save_appointment(
        Appointment(
            appointment_id="a2",
            ticket_number="TK-0002",
            vertical="it_support",
            appointment_type="remote_session",
            status=AppointmentStatus.PROPOSED,
        )
    )
    await repo.save_appointment(make_appointment(appointment_id="a3", vertical="dental_clinic"))

    results = await repo.list_appointments_for_ticket("TK-0001", vertical="it_support")
    assert {a.appointment_id for a in results} == {"a1"}


async def test_list_appointments_filters_by_date_range_and_status(repo: InMemoryRepo):
    confirmed_in_range = make_appointment(appointment_id="a1").model_copy(
        update={
            "status": AppointmentStatus.CONFIRMED,
            "confirmed_slot": TimeSlot(
                start=datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
                end=datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc),
            ),
        }
    )
    confirmed_out_of_range = make_appointment(appointment_id="a2").model_copy(
        update={
            "status": AppointmentStatus.CONFIRMED,
            "confirmed_slot": TimeSlot(
                start=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
                end=datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc),
            ),
        }
    )
    still_proposed = make_appointment(appointment_id="a3")  # no confirmed_slot

    for appt in (confirmed_in_range, confirmed_out_of_range, still_proposed):
        await repo.save_appointment(appt)

    results = await repo.list_appointments(
        "it_support",
        from_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        to_date=datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    assert {a.appointment_id for a in results} == {"a1"}

    results = await repo.list_appointments(
        "it_support",
        from_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        to_date=datetime(2026, 9, 30, tzinfo=timezone.utc),
        status=AppointmentStatus.PROPOSED,
    )
    assert results == []
