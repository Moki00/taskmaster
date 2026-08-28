"""Thin async wrapper around Gemini 3.5. Enforces structured JSON output - agents get back a
validated Pydantic model, never free text to parse themselves.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, TypeVar, get_origin

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, create_model

from app.config import settings
from app.core.retry import call_with_retry
from app.core.timing import timed_stage

T = TypeVar("T", bound=BaseModel)


class _KeyValue(BaseModel):
    key: str
    value: str


def _dict_field_names(model: type[BaseModel]) -> set[str]:
    return {name for name, field in model.model_fields.items() if get_origin(field.annotation) is dict}


def _needs_wire_schema(model: type[BaseModel]) -> bool:
    return model.model_config.get("extra") == "forbid" or bool(_dict_field_names(model))


@lru_cache(maxsize=None)
def _wire_schema(model: type[BaseModel]) -> type[BaseModel]:
    """Gemini's Developer API (API-key auth, as opposed to Vertex AI) rejects any response_schema
    whose JSON schema includes `additionalProperties`. Pydantic emits that both for models with
    `extra="forbid"` (every TaskmasterModel our agents use) and, unavoidably, for any `dict[str, X]`
    field (an open-ended object has no other way to express "any key allowed"). Returns a
    structurally adapted, permissive twin to request the response against: forbid is dropped, and
    each dict field becomes a `list[_KeyValue]` (Gemini can express a list of fixed-shape objects
    fine, just not a wildcard map). generate_structured converts the pairs back to a dict and
    re-validates into the real, strict `model` before returning, so callers never see the twin.

    Cached per model class so the twin's identity is stable - both for a cheap no-op on repeat
    calls, and so tests mocking the SDK boundary can recognize which strict model a captured
    response_schema corresponds to.
    """
    if not _needs_wire_schema(model):
        return model
    dict_fields = _dict_field_names(model)
    fields = {
        name: (list[_KeyValue], Field(default_factory=list)) if name in dict_fields else (field.annotation, field)
        for name, field in model.model_fields.items()
    }
    return create_model(f"_{model.__name__}Wire", **fields)  # type: ignore[call-overload]


def _from_wire(model: type[BaseModel], parsed: BaseModel) -> dict[str, Any]:
    """Converts a wire-schema instance's dump back into `model`'s shape - list[_KeyValue] pairs
    become plain dicts again - ready for `model.model_validate(...)`.
    """
    dump = parsed.model_dump()
    for name in _dict_field_names(model):
        value = dump.get(name)
        if isinstance(value, list):  # wire shape: list of {"key": ..., "value": ...} pairs
            dump[name] = {pair["key"]: pair["value"] for pair in value}
    return dump


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
        wire_schema = _wire_schema(response_schema)

        async with timed_stage("gemini.generate_structured", correlation_id=correlation_id, model=self._model):
            response = await call_with_retry(
                lambda: self._client.aio.models.generate_content(
                    model=self._model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=wire_schema,
                    ),
                ),
                operation="gemini.generate_structured",
                retryable_exceptions=(errors.ServerError,),
            )

        if response.parsed is not None:
            parsed = response.parsed
        else:
            # Safety net, not the primary path: some responses may not populate .parsed even with
            # a schema set.
            parsed = wire_schema.model_validate_json(response.text)

        if wire_schema is response_schema:
            return parsed
        return response_schema.model_validate(_from_wire(response_schema, parsed))

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
