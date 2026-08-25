"""The one place timeout + retry + structured logging lives for external calls. Every client in
app/integrations/ calls through call_with_retry instead of reimplementing this.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

from app.core.errors import IntegrationTimeoutError, IntegrationUnavailableError

log = structlog.get_logger("taskmaster.retry")

T = TypeVar("T")


async def call_with_retry(
    func: Callable[[], Awaitable[T]],
    *,
    operation: str,
    attempts: int = 3,
    timeout_seconds: float = 10.0,
    backoff_base_seconds: float = 0.5,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Calls func() up to `attempts` times, each under a `timeout_seconds` budget.

    Retries (with exponential backoff) on a timeout or on any exception matching
    `retryable_exceptions`; anything else propagates immediately. Exhausting every attempt raises
    IntegrationTimeoutError (last failure was a timeout) or IntegrationUnavailableError (last
    failure was a caught exception), chaining the original exception.
    """
    last_exc: Exception | None = None
    last_was_timeout = False

    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.wait_for(func(), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            last_exc = exc
            last_was_timeout = True
            log.warning(
                "integration_call_timed_out",
                operation=operation,
                attempt=attempt,
                attempts=attempts,
                timeout_seconds=timeout_seconds,
            )
        except retryable_exceptions as exc:
            last_exc = exc
            last_was_timeout = False
            log.warning(
                "integration_call_failed",
                operation=operation,
                attempt=attempt,
                attempts=attempts,
                error=str(exc),
            )

        if attempt < attempts:
            await asyncio.sleep(backoff_base_seconds * (2 ** (attempt - 1)))

    assert last_exc is not None
    if last_was_timeout:
        raise IntegrationTimeoutError(f"{operation} timed out after {attempts} attempts") from last_exc
    raise IntegrationUnavailableError(f"{operation} failed after {attempts} attempts: {last_exc}") from last_exc
