"""Thin async wrapper around Gemini 3.5. Enforces structured JSON output - agents get back a
validated Pydantic model, never free text to parse themselves.
"""
from __future__ import annotations

from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import settings
from app.core.retry import call_with_retry
from app.core.timing import timed_stage

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    def __init__(self) -> None:
        # GEMINI_API_KEY is required in Settings (fails loudly at startup if unset), never None here.
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_content: str,
        response_schema: type[T],
        correlation_id: str | None = None,
    ) -> T:
        """Calls Gemini with structured-output enforcement. Returns a validated response_schema
        instance - never raw text for the caller to parse.
        """
        async with timed_stage("gemini.generate_structured", correlation_id=correlation_id, model=self._model):
            response = await call_with_retry(
                lambda: self._client.aio.models.generate_content(
                    model=self._model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                ),
                operation="gemini.generate_structured",
                retryable_exceptions=(errors.ServerError,),
            )

        if response.parsed is not None:
            return response.parsed
        # Safety net, not the primary path: some responses may not populate .parsed even with a
        # schema set.
        return response_schema.model_validate_json(response.text)

    async def transcribe_audio(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        correlation_id: str | None = None,
    ) -> str:
        """Gemini audio understanding - returns a transcript, for the Intake Agent's voice channel."""
        async with timed_stage("gemini.transcribe_audio", correlation_id=correlation_id, model=self._model):
            response = await call_with_retry(
                lambda: self._client.aio.models.generate_content(
                    model=self._model,
                    contents=[
                        "Transcribe this audio message verbatim. Return only the transcript text.",
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    ],
                ),
                operation="gemini.transcribe_audio",
                retryable_exceptions=(errors.ServerError,),
            )
        return response.text


_client_instance: GeminiClient | None = None


def get_gemini_client() -> GeminiClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = GeminiClient()
    return _client_instance
