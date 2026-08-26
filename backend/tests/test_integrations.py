"""Integration client tests. No real credentials exist, so every test mocks the underlying SDK
call - none of these ever reach a live service.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.config import settings
from app.core.errors import ConfigurationError, IntegrationTimeoutError, IntegrationUnavailableError
from app.core.retry import call_with_retry
from app.integrations.calendar_client import CalendarClient
from app.integrations.gemini_client import GeminiClient
from app.integrations.gmail_client import GmailClient
from app.integrations.google_auth import build_google_credentials
from app.integrations.twilio_client import TwilioClient


# --- retry ------------------------------------------------------------------------


async def test_call_with_retry_succeeds_first_try():
    async def fn() -> str:
        return "ok"

    assert await call_with_retry(fn, operation="test.op") == "ok"


async def test_call_with_retry_succeeds_after_failures():
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    result = await call_with_retry(fn, operation="test.op", attempts=5, backoff_base_seconds=0.01)
    assert result == "ok"
    assert calls["n"] == 3


async def test_call_with_retry_exhausts_attempts_raises_unavailable():
    async def fn() -> None:
        raise ValueError("boom")

    with pytest.raises(IntegrationUnavailableError):
        await call_with_retry(fn, operation="test.op", attempts=2, backoff_base_seconds=0.01)


async def test_call_with_retry_timeout_raises_integration_timeout():
    async def fn() -> None:
        await asyncio.sleep(1)

    with pytest.raises(IntegrationTimeoutError):
        await call_with_retry(fn, operation="test.op", attempts=1, timeout_seconds=0.05)


async def test_call_with_retry_non_retryable_exception_propagates_immediately():
    calls = {"n": 0}

    async def fn() -> None:
        calls["n"] += 1
        raise KeyError("nope")

    with pytest.raises(KeyError):
        await call_with_retry(fn, operation="test.op", attempts=5, retryable_exceptions=(ValueError,))
    assert calls["n"] == 1


# --- GeminiClient -------------------------------------------------------------------


class _SampleSchema(BaseModel):
    value: str


async def test_generate_structured_returns_parsed():
    client = GeminiClient()
    fake_response = SimpleNamespace(parsed=_SampleSchema(value="hi"), text='{"value": "hi"}')
    client._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    result = await client.generate_structured(
        system_prompt="sys", user_content="hello", response_schema=_SampleSchema
    )
    assert result == _SampleSchema(value="hi")


async def test_generate_structured_falls_back_when_parsed_is_none():
    client = GeminiClient()
    fake_response = SimpleNamespace(parsed=None, text='{"value": "fallback"}')
    client._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    result = await client.generate_structured(
        system_prompt="sys", user_content="hello", response_schema=_SampleSchema
    )
    assert result.value == "fallback"


async def test_generate_structured_retries_through_server_error():
    client = GeminiClient()
    fake_response = SimpleNamespace(parsed=_SampleSchema(value="ok"), text="")
    mock = AsyncMock(side_effect=[genai_errors.ServerError(500, {"message": "err"}), fake_response])
    client._client.aio.models.generate_content = mock

    result = await client.generate_structured(
        system_prompt="sys", user_content="hello", response_schema=_SampleSchema
    )
    assert result.value == "ok"
    assert mock.call_count == 2


async def test_generate_structured_sends_schema_configuration():
    client = GeminiClient()
    generate_content = AsyncMock(return_value=SimpleNamespace(parsed=_SampleSchema(value="ok"), text=""))
    client._client.aio.models.generate_content = generate_content

    await client.generate_structured(
        system_prompt="sys", user_content="hello", response_schema=_SampleSchema
    )

    call = generate_content.await_args
    assert call.kwargs["model"] == settings.GEMINI_MODEL
    assert call.kwargs["contents"] == "hello"
    config = call.kwargs["config"]
    assert config.system_instruction == "sys"
    assert config.response_mime_type == "application/json"
    assert config.response_schema is _SampleSchema


async def test_transcribe_audio_returns_text():
    client = GeminiClient()
    fake_response = SimpleNamespace(text="hello world")
    client._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    transcript = await client.transcribe_audio(audio_bytes=b"fake-audio", mime_type="audio/wav")
    assert transcript == "hello world"


# --- GmailClient ---------------------------------------------------------------------


def _configure_gmail_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "fake-refresh-token")
    monkeypatch.setattr(settings, "GMAIL_SENDER_EMAIL", "sender@example.com")


async def test_gmail_client_missing_config_raises():
    with pytest.raises(ConfigurationError):
        GmailClient()


async def test_gmail_client_send_email_returns_message_id(monkeypatch: pytest.MonkeyPatch):
    _configure_gmail_env(monkeypatch)
    with patch("app.integrations.gmail_client.build") as mock_build:
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "msg-123"
        }
        mock_build.return_value = mock_service

        client = GmailClient()
        message_id = await client.send_email(to="a@example.com", subject="hi", body_text="hello")
        assert message_id == "msg-123"


async def test_gmail_client_send_email_uses_to_thread(monkeypatch: pytest.MonkeyPatch):
    _configure_gmail_env(monkeypatch)
    with patch("app.integrations.gmail_client.build") as mock_build:
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "msg-1"
        }
        mock_build.return_value = mock_service
        client = GmailClient()

        with patch("app.integrations.gmail_client.asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
            await client.send_email(to="a@example.com", subject="hi", body_text="hello")
            assert mock_to_thread.called


async def test_gmail_client_get_message_returns_message_resource(monkeypatch: pytest.MonkeyPatch):
    _configure_gmail_env(monkeypatch)
    with patch("app.integrations.gmail_client.build") as mock_build:
        mock_service = MagicMock()
        expected = {"id": "msg-1", "payload": {"headers": []}}
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = expected
        mock_build.return_value = mock_service

        client = GmailClient()
        result = await client.get_message("msg-1")

        assert result == expected
        mock_service.users.return_value.messages.return_value.get.assert_called_once_with(
            userId="me", id="msg-1"
        )


async def test_gmail_client_list_history_follows_next_page_tokens(monkeypatch: pytest.MonkeyPatch):
    _configure_gmail_env(monkeypatch)
    with patch("app.integrations.gmail_client.build") as mock_build:
        mock_service = MagicMock()
        history_list = mock_service.users.return_value.history.return_value.list
        history_list.return_value.execute.side_effect = [
            {
                "history": [{"messagesAdded": [{"message": {"id": "msg-1"}}]}],
                "nextPageToken": "page-2",
            },
            {"history": [{"messagesAdded": [{"message": {"id": "msg-2"}}]}]},
        ]
        mock_build.return_value = mock_service

        client = GmailClient()
        result = await client.list_history(start_history_id="100")

        assert result == ["msg-1", "msg-2"]
        assert history_list.call_count == 2
        assert history_list.call_args_list[0].kwargs == {"userId": "me", "startHistoryId": "100"}
        assert history_list.call_args_list[1].kwargs["pageToken"] == "page-2"


async def test_build_google_credentials_uses_requested_oauth_settings(monkeypatch: pytest.MonkeyPatch):
    _configure_gmail_env(monkeypatch)

    credentials = build_google_credentials(required_scopes=["scope.one", "scope.two"])

    assert credentials.token is None
    assert credentials.refresh_token == "fake-refresh-token"
    assert credentials.client_id == "fake-client-id"
    assert credentials.client_secret == "fake-secret"
    assert credentials.token_uri == "https://oauth2.googleapis.com/token"
    assert credentials.scopes == ["scope.one", "scope.two"]


async def test_build_google_credentials_reports_all_missing_settings(monkeypatch: pytest.MonkeyPatch):
    for name in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
        monkeypatch.setattr(settings, name, None)

    with pytest.raises(ConfigurationError, match="GMAIL_CLIENT_ID.*GMAIL_CLIENT_SECRET.*GMAIL_REFRESH_TOKEN"):
        build_google_credentials(required_scopes=["scope"])


# --- CalendarClient ------------------------------------------------------------------


def _configure_calendar_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "fake-refresh-token")
    monkeypatch.setattr(settings, "CALENDAR_ID", "cal-1")


async def test_calendar_client_missing_config_raises():
    with pytest.raises(ConfigurationError):
        CalendarClient()


async def test_calendar_client_get_available_slots_computes_gaps(monkeypatch: pytest.MonkeyPatch):
    _configure_calendar_env(monkeypatch)
    with patch("app.integrations.calendar_client.build") as mock_build:
        mock_service = MagicMock()
        busy = [{"start": "2026-09-01T10:00:00+00:00", "end": "2026-09-01T11:00:00+00:00"}]
        mock_service.freebusy.return_value.query.return_value.execute.return_value = {
            "calendars": {"cal-1": {"busy": busy}}
        }
        mock_build.return_value = mock_service

        client = CalendarClient()
        slots = await client.get_available_slots(
            start=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
            duration_minutes=30,
        )

        assert len(slots) == 2
        assert slots[0].start == datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
        assert slots[1].start == datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)


async def test_calendar_client_get_available_slots_merges_overlapping_busy_blocks(
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_calendar_env(monkeypatch)
    with patch("app.integrations.calendar_client.build") as mock_build:
        mock_service = MagicMock()
        mock_service.freebusy.return_value.query.return_value.execute.return_value = {
            "calendars": {
                "cal-1": {
                    "busy": [
                        {"start": "2026-09-01T10:00:00+00:00", "end": "2026-09-01T11:00:00+00:00"},
                        {"start": "2026-09-01T10:30:00+00:00", "end": "2026-09-01T12:00:00+00:00"},
                    ]
                }
            }
        }
        mock_build.return_value = mock_service

        client = CalendarClient()
        slots = await client.get_available_slots(
            start=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, 13, 0, tzinfo=timezone.utc),
            duration_minutes=30,
        )

        assert [(slot.start, slot.end) for slot in slots] == [
            (
                datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
                datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc),
            ),
            (
                datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
                datetime(2026, 9, 1, 12, 30, tzinfo=timezone.utc),
            ),
        ]


async def test_calendar_client_get_available_slots_handles_empty_calendar(
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_calendar_env(monkeypatch)
    with patch("app.integrations.calendar_client.build") as mock_build:
        mock_service = MagicMock()
        query = mock_service.freebusy.return_value.query
        query.return_value.execute.return_value = {"calendars": {"cal-1": {"busy": []}}}
        mock_build.return_value = mock_service

        client = CalendarClient()
        slots = await client.get_available_slots(
            start=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            duration_minutes=30,
        )

        assert [(slot.start, slot.end) for slot in slots] == [
            (
                datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
                datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc),
            )
        ]
        query.assert_called_once()
        assert query.call_args.kwargs["body"]["items"] == [{"id": "cal-1"}]


async def test_calendar_client_create_event_returns_event_id(monkeypatch: pytest.MonkeyPatch):
    from app.models import TimeSlot

    _configure_calendar_env(monkeypatch)
    with patch("app.integrations.calendar_client.build") as mock_build:
        mock_service = MagicMock()
        mock_service.events.return_value.insert.return_value.execute.return_value = {"id": "evt-1"}
        mock_build.return_value = mock_service

        client = CalendarClient()
        slot = TimeSlot(
            start=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
        )
        event_id = await client.create_event(slot=slot, summary="Onsite visit", description="repair")
        assert event_id == "evt-1"


# --- TwilioClient ---------------------------------------------------------------------


def _configure_twilio_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC" + "f" * 32)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "fake-token")
    monkeypatch.setattr(settings, "TWILIO_FROM_NUMBER", "+15550000000")


async def test_twilio_client_missing_config_raises():
    with pytest.raises(ConfigurationError):
        TwilioClient()


async def test_twilio_client_send_sms_returns_sid(monkeypatch: pytest.MonkeyPatch):
    _configure_twilio_env(monkeypatch)
    client = TwilioClient()
    client._client.messages.create_async = AsyncMock(return_value=SimpleNamespace(sid="SM123"))

    sid = await client.send_sms(to="+15551234567", body="hello")
    assert sid == "SM123"


async def test_twilio_client_initiate_voice_call_returns_sid(monkeypatch: pytest.MonkeyPatch):
    _configure_twilio_env(monkeypatch)
    client = TwilioClient()
    client._client.calls.create_async = AsyncMock(return_value=SimpleNamespace(sid="CA123"))

    sid = await client.initiate_voice_call(to="+15551234567", twiml_url="https://example.com/twiml")
    assert sid == "CA123"


async def test_twilio_client_fetch_recording_audio_downloads_mp3_with_auth(
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_twilio_env(monkeypatch)
    client = TwilioClient()
    client._client.recordings.return_value.fetch_async = AsyncMock(
        return_value=SimpleNamespace(
            uri="/2010-04-01/Accounts/ACffffffffffffffffffffffffffffffff/Recordings/RE123.json"
        )
    )

    response = MagicMock(content=b"audio-bytes")
    http_client = MagicMock()
    http_client.get = AsyncMock(return_value=response)
    async_client = MagicMock()
    async_client.__aenter__ = AsyncMock(return_value=http_client)
    async_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.integrations.twilio_client.httpx.AsyncClient", return_value=async_client):
        result = await client.fetch_recording_audio(recording_sid="RE123")

    assert result == b"audio-bytes"
    response.raise_for_status.assert_called_once_with()
    http_client.get.assert_awaited_once_with(
        "https://api.twilio.com/2010-04-01/Accounts/ACffffffffffffffffffffffffffffffff/Recordings/RE123.mp3",
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
    )
