"""Stage timing for the agent pipeline.

`timed_stage` is what makes the sub-30-second claim measurable: wrap every agent stage in it
and every stage emits a structured log line plus an event on `event_bus`, which the demo UI
(or anything else) can subscribe to for live pipeline progress.
"""
from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger("taskmaster.timing")


@dataclass(frozen=True, slots=True)
class StageEvent:
    stage: str
    elapsed_ms: float
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


Subscriber = Callable[[StageEvent], Any | Awaitable[Any]]


class EventBus:
    """In-memory pub/sub for pipeline stage events. Subscribers may be sync or async callables."""

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []

    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:
        self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

        return unsubscribe

    def publish(self, event: StageEvent) -> None:
        for subscriber in list(self._subscribers):
            result = subscriber(event)
            if inspect.isawaitable(result):
                asyncio.ensure_future(result)


event_bus = EventBus()


@asynccontextmanager
async def timed_stage(
    stage: str,
    correlation_id: str | None = None,
    **metadata: Any,
) -> AsyncIterator[str]:
    """Times a pipeline stage. Yields the correlation_id in use (generated if not passed in).

    On exit, logs {stage, elapsed_ms, correlation_id} via structlog and publishes a StageEvent
    to `event_bus`, timing runs even if the stage raises.
    """
    cid = correlation_id or str(uuid.uuid4())
    start = time.perf_counter()
    try:
        yield cid
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info("stage_completed", stage=stage, elapsed_ms=elapsed_ms, correlation_id=cid, **metadata)
        event_bus.publish(
            StageEvent(stage=stage, elapsed_ms=elapsed_ms, correlation_id=cid, metadata=metadata)
        )
