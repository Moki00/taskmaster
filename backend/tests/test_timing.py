"""Tests for stage timing and event publication."""
from __future__ import annotations

from app.core.timing import StageEvent, event_bus, timed_stage


async def test_timed_stage_publishes_event_with_stage_details():
    events: list[StageEvent] = []
    unsubscribe = event_bus.subscribe(events.append)

    try:
        async with timed_stage(
            "classifier_agent",
            correlation_id="intake-123",
            vertical="it_support",
        ) as correlation_id:
            assert correlation_id == "intake-123"

        assert len(events) == 1
        event = events[0]
        assert event.stage == "classifier_agent"
        assert event.correlation_id == "intake-123"
        assert event.elapsed_ms >= 0
        assert event.metadata == {"vertical": "it_support"}
    finally:
        unsubscribe()
