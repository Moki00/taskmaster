"""Thin async wrapper around the Google Calendar API. Sync SDK, so every call runs via
asyncio.to_thread - never blocks the event loop.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.core.errors import ConfigurationError
from app.core.retry import call_with_retry
from app.core.timing import timed_stage
from app.integrations.google_auth import build_google_credentials
from app.models import TimeSlot

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarClient:
    def __init__(self) -> None:
        if not settings.CALENDAR_ID:
            raise ConfigurationError("Missing required environment variable for Calendar: CALENDAR_ID")
        credentials = build_google_credentials(required_scopes=_SCOPES)
        self._service = build("calendar", "v3", credentials=credentials)
        self._calendar_id = settings.CALENDAR_ID

    async def get_available_slots(
        self,
        *,
        start: datetime,
        end: datetime,
        duration_minutes: int,
        correlation_id: str | None = None,
    ) -> list[TimeSlot]:
        """Proposes one TimeSlot per free gap in [start, end] long enough to fit duration_minutes.

        Simplification: proposes the earliest slot within each open gap rather than packing
        multiple back-to-back slots into a single long gap.
        """

        def _do_query() -> dict:
            return (
                self._service.freebusy()
                .query(
                    body={
                        "timeMin": start.isoformat(),
                        "timeMax": end.isoformat(),
                        "items": [{"id": self._calendar_id}],
                    }
                )
                .execute()
            )

        async with timed_stage("calendar.get_available_slots", correlation_id=correlation_id):
            response = await call_with_retry(
                lambda: asyncio.to_thread(_do_query),
                operation="calendar.get_available_slots",
                retryable_exceptions=(HttpError, OSError),
            )

        busy_blocks = response["calendars"][self._calendar_id]["busy"]
        busy = sorted(
            (
                (datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"]))
                for b in busy_blocks
            ),
            key=lambda pair: pair[0],
        )

        duration = timedelta(minutes=duration_minutes)
        slots: list[TimeSlot] = []
        cursor = start
        for busy_start, busy_end in busy:
            if busy_start - cursor >= duration:
                slots.append(TimeSlot(start=cursor, end=cursor + duration))
            cursor = max(cursor, busy_end)
        if end - cursor >= duration:
            slots.append(TimeSlot(start=cursor, end=cursor + duration))
        return slots

    async def create_event(
        self,
        *,
        slot: TimeSlot,
        summary: str,
        description: str,
        correlation_id: str | None = None,
    ) -> str:
        """Inserts a confirmed event, returns its Google Calendar event id."""

        def _do_insert() -> dict:
            return (
                self._service.events()
                .insert(
                    calendarId=self._calendar_id,
                    body={
                        "summary": summary,
                        "description": description,
                        "start": {"dateTime": slot.start.isoformat()},
                        "end": {"dateTime": slot.end.isoformat()},
                    },
                )
                .execute()
            )

        async with timed_stage("calendar.create_event", correlation_id=correlation_id):
            event = await call_with_retry(
                lambda: asyncio.to_thread(_do_insert),
                operation="calendar.create_event",
                retryable_exceptions=(HttpError, OSError),
            )
        return event["id"]


_client_instance: CalendarClient | None = None


def get_calendar_client() -> CalendarClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = CalendarClient()
    return _client_instance
