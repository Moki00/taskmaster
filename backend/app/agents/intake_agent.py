"""Intake Agent: normalizes messages from every channel (including audio) into the one
internal schema (NormalizedMessage) that every downstream agent depends on.

Channel adapters (app/channels/*) are responsible for pulling raw payloads off the wire and
constructing an IntakeInput; this agent never talks to Gmail/Twilio/etc. directly - audio bytes
and text arrive already extracted, keeping this stage's only external dependency Gemini (for
transcription and language detection).
"""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field, model_validator

from app.core.timing import timed_stage
from app.integrations.gemini_client import get_gemini_client
from app.models.base import TaskmasterModel
from app.models.common import Attachment, Sender
from app.models.enums import Channel
from app.models.message import NormalizedMessage

_LANGUAGE_SYSTEM_PROMPT = (
    "You detect the primary human language of a short customer support message. "
    "Respond with the ISO 639-1 two-letter language code only (e.g. 'en', 'es', 'fr'). "
    "If the message is empty, ambiguous, or mostly non-linguistic (e.g. just a phone number), "
    "respond with 'en'."
)


class _LanguageDetection(TaskmasterModel):
    language: str


class IntakeInput(TaskmasterModel):
    """Everything a channel adapter must supply for the Intake Agent to build a
    NormalizedMessage. Exactly one of body_text or audio_bytes must be present - voice channels
    supply audio, every other channel supplies text.
    """

    channel: Channel
    vertical: str
    sender: Sender = Field(default_factory=Sender)
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    audio_bytes: bytes | None = None
    audio_mime_type: str | None = None
    audio_ref: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_has_content(self) -> "IntakeInput":
        if not self.body_text and not self.audio_bytes:
            raise ValueError("IntakeInput requires body_text or audio_bytes")
        if self.audio_bytes and not self.audio_mime_type:
            raise ValueError("audio_mime_type is required when audio_bytes is supplied")
        return self


async def _detect_language(text: str, *, correlation_id: str) -> str | None:
    """Best-effort language detection. Never fails the pipeline - a detection failure just
    leaves NormalizedMessage.language unset rather than blocking intake.
    """
    if not text.strip():
        return None
    try:
        client = get_gemini_client()
        result = await client.generate_structured(
            system_prompt=_LANGUAGE_SYSTEM_PROMPT,
            user_content=text[:500],
            response_schema=_LanguageDetection,
            correlation_id=correlation_id,
        )
        return result.language.strip().lower()[:2] or None
    except Exception:
        return None


async def run(intake_input: IntakeInput, *, correlation_id: str | None = None) -> NormalizedMessage:
    """Builds a NormalizedMessage from raw channel input: transcribes audio if present, detects
    language, and assigns the intake_id/correlation_id that ties this message to every downstream
    pipeline stage.
    """
    intake_id = correlation_id or f"intake-{uuid.uuid4().hex[:8]}"

    async with timed_stage("intake_agent", correlation_id=intake_id, channel=intake_input.channel.value):
        body_text = intake_input.body_text
        transcript: str | None = None
        audio_ref = intake_input.audio_ref

        if intake_input.audio_bytes:
            client = get_gemini_client()
            transcript = await client.transcribe_audio(
                audio_bytes=intake_input.audio_bytes,
                mime_type=intake_input.audio_mime_type,  # type: ignore[arg-type]
                correlation_id=intake_id,
            )
            body_text = body_text or transcript

        language = await _detect_language(body_text or "", correlation_id=intake_id)

        return NormalizedMessage(
            intake_id=intake_id,
            vertical=intake_input.vertical,
            channel=intake_input.channel,
            sender=intake_input.sender,
            subject=intake_input.subject,
            body_text=body_text or "",
            body_html=intake_input.body_html,
            language=language,
            transcript=transcript,
            audio_ref=audio_ref,
            attachments=intake_input.attachments,
            raw_payload=intake_input.raw_payload,
        )
