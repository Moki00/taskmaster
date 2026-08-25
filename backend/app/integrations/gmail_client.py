"""Thin async wrapper around the Gmail API. googleapiclient is sync-only, so every call runs via
asyncio.to_thread - never blocks the event loop.
"""
from __future__ import annotations

import asyncio
import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.core.errors import ConfigurationError
from app.core.retry import call_with_retry
from app.core.timing import timed_stage
from app.integrations.google_auth import build_google_credentials

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailClient:
    def __init__(self) -> None:
        if not settings.GMAIL_SENDER_EMAIL:
            raise ConfigurationError("Missing required environment variable for Gmail: GMAIL_SENDER_EMAIL")
        credentials = build_google_credentials(required_scopes=_SCOPES)
        self._service = build("gmail", "v1", credentials=credentials)
        self._sender_email = settings.GMAIL_SENDER_EMAIL

    async def send_email(
        self, *, to: str, subject: str, body_text: str, correlation_id: str | None = None
    ) -> str:
        """Sends an email, returns the sent message's Gmail message id.

        Does NOT check settings.AUTO_SEND_REPLIES - that's a pipeline-level decision for the Reply
        Agent to make before calling this at all; this client stays an honest, unconditional wrapper.
        """
        message = MIMEText(body_text)
        message["to"] = to
        message["from"] = self._sender_email
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        def _do_send() -> dict:
            return self._service.users().messages().send(userId="me", body={"raw": raw}).execute()

        async with timed_stage("gmail.send_email", correlation_id=correlation_id):
            response = await call_with_retry(
                lambda: asyncio.to_thread(_do_send),
                operation="gmail.send_email",
                retryable_exceptions=(HttpError, OSError),
            )
        return response["id"]

    async def get_message(self, message_id: str, *, correlation_id: str | None = None) -> dict:
        """Fetches a raw Gmail message resource - used to pull full content after a Pub/Sub
        history notification (channels/email_gmail.py's job to parse that envelope, not this).
        """

        def _do_get() -> dict:
            return self._service.users().messages().get(userId="me", id=message_id).execute()

        async with timed_stage("gmail.get_message", correlation_id=correlation_id):
            return await call_with_retry(
                lambda: asyncio.to_thread(_do_get),
                operation="gmail.get_message",
                retryable_exceptions=(HttpError, OSError),
            )

    async def list_history(self, *, start_history_id: str, correlation_id: str | None = None) -> list[str]:
        """Returns message ids added since start_history_id, per Gmail's history.list API - the
        mechanism Pub/Sub push notifications point at.
        """

        def _do_list() -> dict:
            return self._service.users().history().list(userId="me", startHistoryId=start_history_id).execute()

        async with timed_stage("gmail.list_history", correlation_id=correlation_id):
            response = await call_with_retry(
                lambda: asyncio.to_thread(_do_list),
                operation="gmail.list_history",
                retryable_exceptions=(HttpError, OSError),
            )

        message_ids: list[str] = []
        for record in response.get("history", []):
            for added in record.get("messagesAdded", []):
                message_ids.append(added["message"]["id"])
        return message_ids


_client_instance: GmailClient | None = None


def get_gmail_client() -> GmailClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = GmailClient()
    return _client_instance
