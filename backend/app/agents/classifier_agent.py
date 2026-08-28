"""Classifier Agent: the core NLU stage. Uses Gemini 3.5 to read a messy, possibly angry,
possibly multilingual customer message and classify it against the ACTIVE vertical's taxonomy -
issue_type, urgency, entities, sentiment, and a calibrated confidence score.

Nothing vertical-specific is hardcoded here: the entire prompt (taxonomy, urgency definitions,
required entities) is built from VerticalConfig data, so swapping ACTIVE_VERTICAL changes what
this agent classifies against with zero code changes.
"""
from __future__ import annotations

import structlog
from pydantic import ValidationError

from app.core.timing import timed_stage
from app.integrations.gemini_client import get_gemini_client
from app.models.classification import Classification
from app.models.enums import Sentiment, Urgency
from app.models.message import NormalizedMessage
from app.verticals.base import VerticalConfig
from app.verticals.loader import get_active_vertical

log = structlog.get_logger("taskmaster.classifier_agent")

_MAX_ATTEMPTS = 2


def _build_system_prompt(vertical: VerticalConfig, *, correction: str | None = None) -> str:
    issue_type_lines = "\n".join(
        f"- {it.name}: {it.description}" + (f" Examples: {'; '.join(it.examples)}" if it.examples else "")
        for it in vertical.issue_types
    )
    urgency_lines = "\n".join(
        f"- {rule.level.value}: {rule.definition}"
        + (f" Examples: {'; '.join(rule.concrete_examples)}" if rule.concrete_examples else "")
        for rule in vertical.urgency_rules
    )
    entity_lines = "\n".join(f"- {e.name}: {e.description}" for e in vertical.required_entities) or "(none defined)"

    prompt = f"""You are the AI triage classifier for {vertical.display_name}. {vertical.business_description}

Read the customer's message (it may be terse, angry, multilingual, or half-finished) and classify
it into the structured schema below. Use ONLY the taxonomy given here - never invent categories.

Issue types (choose exactly one `issue_type`, using the name below verbatim):
{issue_type_lines}

Urgency levels (choose exactly one `urgency`):
{urgency_lines}

Entities relevant to this vertical - record any you find in `extracted_details` (keyed by the
entity name below), and list every one you could NOT find in `missing_info` (using the name
verbatim):
{entity_lines}

Also determine:
- `summary`: a clean 1-2 sentence synopsis of the request.
- `sentiment`: exactly one of CALM, ANNOYED, FRUSTRATED, ANGRY - the customer's emotional state.
- `frustration_score`: 0.0-1.0, calibrated to how frustrated/urgent the tone reads.
- `business_impact`: one short phrase describing the operational impact if left unresolved.
- `confidence`: 0.0-1.0, your genuine confidence in this classification.
- `reasoning`: 1-2 sentences on why you chose this issue_type and urgency."""

    if correction:
        prompt += f"\n\nIMPORTANT: your previous response was rejected: {correction}\nFollow the schema and the exact names listed above exactly."
    return prompt


def _build_user_content(message: NormalizedMessage) -> str:
    parts = []
    if message.sender.name or message.sender.company:
        who = ", ".join(filter(None, [message.sender.name, message.sender.company]))
        parts.append(f"From: {who}")
    if message.language:
        parts.append(f"Detected language: {message.language}")
    if message.subject:
        parts.append(f"Subject: {message.subject}")
    parts.append(f"Message:\n{message.body_text}")
    return "\n".join(parts)


def _fallback_issue_type(vertical: VerticalConfig) -> str:
    names = vertical.issue_type_names
    if "other" in names:
        return "other"
    return vertical.issue_types[0].name


def _fallback_classification(vertical: VerticalConfig, reason: str) -> Classification:
    """A safe, low-confidence Classification used only when Gemini's output can't be coerced into
    a valid schema after retrying - keeps the pipeline moving (flagged for human review downstream
    via its low confidence) instead of crashing the whole request.
    """
    log.warning("classifier_agent_fallback_used", reason=reason)
    return Classification(
        issue_type=_fallback_issue_type(vertical),
        urgency=Urgency.MEDIUM,
        summary="Automatic classification failed; needs manual review.",
        extracted_details={},
        missing_info=["classification_failed"],
        sentiment=Sentiment.CALM,
        frustration_score=0.5,
        business_impact="Unknown - automatic classification failed.",
        confidence=0.0,
        reasoning=f"Fallback classification used after classifier errors: {reason}",
    )


async def run(
    message: NormalizedMessage,
    *,
    vertical: VerticalConfig | None = None,
    correlation_id: str | None = None,
) -> Classification:
    """Classifies a NormalizedMessage against the active vertical's taxonomy. Always returns a
    valid Classification - a low-confidence fallback is used if Gemini can't be coerced into the
    schema after one retry, rather than raising and failing the whole pipeline.
    """
    vertical = vertical or get_active_vertical()
    client = get_gemini_client()
    cid = correlation_id or message.intake_id

    async with timed_stage("classifier_agent", correlation_id=cid, vertical=vertical.key):
        correction: str | None = None
        last_error: str = ""
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                raw = await client.generate_structured(
                    system_prompt=_build_system_prompt(vertical, correction=correction),
                    user_content=_build_user_content(message),
                    response_schema=Classification,
                    correlation_id=cid,
                )
                return Classification.model_validate(
                    raw.model_dump(), context={"valid_issue_types": vertical.issue_type_names}
                )
            except ValidationError as exc:
                last_error = str(exc)
                correction = last_error
                log.warning(
                    "classifier_agent_invalid_output", attempt=attempt, attempts=_MAX_ATTEMPTS, error=last_error
                )

        return _fallback_classification(vertical, last_error)
