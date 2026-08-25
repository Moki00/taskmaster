"""Thin async wrapper around Twilio (SMS + voice). Twilio's SDK has native async methods
(create_async, fetch_async) - no thread-pool wrapping needed, unlike the Google API clients.
"""
from __future__ import annotations

import httpx
from twilio.base.exceptions import TwilioException
from twilio.rest import Client

from app.config import settings
from app.core.errors import ConfigurationError
from app.core.retry import call_with_retry
from app.core.timing import timed_stage


class TwilioClient:
    def __init__(self) -> None:
        missing = [
            name
            for name, value in (
                ("TWILIO_ACCOUNT_SID", settings.TWILIO_ACCOUNT_SID),
                ("TWILIO_AUTH_TOKEN", settings.TWILIO_AUTH_TOKEN),
                ("TWILIO_FROM_NUMBER", settings.TWILIO_FROM_NUMBER),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(f"Missing required environment variable(s) for Twilio: {', '.join(missing)}")

        self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self._from_number = settings.TWILIO_FROM_NUMBER

    async def send_sms(self, *, to: str, body: str, correlation_id: str | None = None) -> str:
        """Sends an SMS, returns the Twilio message SID."""
        async with timed_stage("twilio.send_sms", correlation_id=correlation_id):
            message = await call_with_retry(
                lambda: self._client.messages.create_async(to=to, from_=self._from_number, body=body),
                operation="twilio.send_sms",
                retryable_exceptions=(TwilioException,),
            )
        return message.sid

    async def initiate_voice_call(
        self, *, to: str, twiml_url: str, correlation_id: str | None = None
    ) -> str:
        """Initiates an outbound voice call using a TwiML URL for call flow, returns the call SID.

        Inbound voice webhook handling (generating TwiML responses) is channels/routes territory,
        not this client.
        """
        async with timed_stage("twilio.initiate_voice_call", correlation_id=correlation_id):
            call = await call_with_retry(
                lambda: self._client.calls.create_async(to=to, from_=self._from_number, url=twiml_url),
                operation="twilio.initiate_voice_call",
                retryable_exceptions=(TwilioException,),
            )
        return call.sid

    async def fetch_recording_audio(
        self, *, recording_sid: str, correlation_id: str | None = None
    ) -> bytes:
        """Downloads a call recording's audio bytes - feeds GeminiClient.transcribe_audio for the
        voice channel.
        """
        async with timed_stage("twilio.fetch_recording_audio", correlation_id=correlation_id):
            recording = await call_with_retry(
                lambda: self._client.recordings(recording_sid).fetch_async(),
                operation="twilio.fetch_recording_audio",
                retryable_exceptions=(TwilioException,),
            )
            media_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"

            async def _download() -> bytes:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.get(
                        media_url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    )
                    response.raise_for_status()
                    return response.content

            return await call_with_retry(
                _download,
                operation="twilio.fetch_recording_audio.download",
                retryable_exceptions=(httpx.HTTPError,),
            )


_client_instance: TwilioClient | None = None


def get_twilio_client() -> TwilioClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = TwilioClient()
    return _client_instance
