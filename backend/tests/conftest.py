"""Shared test fixtures. Gemini is always mocked at the SDK boundary
(client._client.aio.models.generate_content) - real GeminiClient/agent logic runs (prompt
building, taxonomy re-validation, retries), only the network call underneath is faked, so no test
needs a real GEMINI_API_KEY.
"""
from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.integrations.gemini_client import _wire_schema, get_gemini_client
from app.models import Classification, ReplyDraft, Sentiment, Urgency


@pytest.fixture(autouse=True)
def _dummy_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Gemini SDK client refuses to construct with an empty api_key, but every test mocks the
    network call at client._client.aio.models.generate_content - so tests never need a real key,
    only a non-empty placeholder for construction to succeed. Provide one when none is configured
    (e.g. a comment-free local .env with GEMINI_API_KEY left blank, or CI with no env at all).
    """
    if not settings.GEMINI_API_KEY:
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-dummy-key")


@pytest.fixture
def mock_gemini(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[type, Callable[[], Any]]], None]:
    """Returns an installer: call it with {response_schema: zero-arg factory} to make every
    generate_structured call for that schema return the factory's result.

    Keys may be the real (extra="forbid") schema - generate_structured actually requests Gemini
    against that schema's permissive `_wire_schema` twin (see gemini_client.py), so the lookup
    falls back to matching by wire-twin identity when a direct match misses.
    """
    client = get_gemini_client()

    def _install(responses: dict[type, Callable[[], Any]]) -> None:
        async def _fake_generate_content(*, model, contents, config):
            schema = config.response_schema
            factory = responses.get(schema)
            if factory is None:
                factory = next(
                    (f for strict, f in responses.items() if _wire_schema(strict) is schema), None
                )
            if factory is None:
                raise AssertionError(f"no mocked Gemini response registered for schema {schema}")
            parsed = factory()
            return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json())

        monkeypatch.setattr(
            client._client.aio.models, "generate_content", AsyncMock(side_effect=_fake_generate_content)
        )

    return _install


@pytest.fixture
def sample_classification() -> Classification:
    return Classification(
        issue_type="network",
        urgency=Urgency.CRITICAL,
        summary="Office network is completely down.",
        extracted_details={"device_type": "Network Switch"},
        missing_info=[],
        sentiment=Sentiment.FRUSTRATED,
        frustration_score=0.8,
        business_impact="Entire office cannot work.",
        confidence=0.92,
        reasoning="Customer reports a total outage affecting the whole office.",
    )


@pytest.fixture
def sample_reply() -> ReplyDraft:
    return ReplyDraft(
        subject="Re: Network outage",
        body="We're on it - a technician has been dispatched and is treating this as a priority.",
        tone="reassuring",
        language="en",
        questions_asked=[],
        includes_scheduling_link=False,
        requires_human_review=False,
    )
