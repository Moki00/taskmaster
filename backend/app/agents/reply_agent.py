"""Reply Agent: writes the customer-facing reply, matching their language, tone, and emotional
state. Complete info -> confirmation + ticket number + expected response time. Missing info ->
at most 3 targeted questions. Never generic - latency and empathy are the product.
"""
from __future__ import annotations

import structlog

from app.config import settings
from app.core.errors import IntegrationError
from app.core.timing import timed_stage
from app.integrations.gemini_client import get_gemini_client
from app.integrations.gmail_client import get_gmail_client
from app.integrations.twilio_client import get_twilio_client
from app.models.classification import Classification
from app.models.enums import Channel, Sentiment
from app.models.message import NormalizedMessage
from app.models.reply import ReplyDraft
from app.models.ticket import Ticket
from app.verticals.base import VerticalConfig
from app.verticals.loader import get_active_vertical

log = structlog.get_logger("taskmaster.reply_agent")

_MAX_QUESTIONS = 3
_LOW_CONFIDENCE_THRESHOLD = 0.4


def _humanize_minutes(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes / 60
    return f"{hours:g} hour{'s' if hours != 1 else ''}"


def _build_system_prompt(vertical: VerticalConfig, classification: Classification, ticket: Ticket) -> str:
    sla = vertical.sla_by_priority[classification.urgency]
    missing = ", ".join(classification.missing_info) if classification.missing_info else None

    info_instruction = (
        f"The customer did NOT provide: {missing}. Ask at most {_MAX_QUESTIONS} short, specific "
        "questions to get exactly this missing information - nothing generic, nothing padded."
        if missing
        else "The customer provided everything needed. Do not ask any questions - confirm the "
        "ticket and give them a clear next step."
    )

    return f"""You are writing a customer reply for {vertical.display_name}. Tone: {vertical.reply_tone}

The customer's message has been triaged as issue_type='{classification.issue_type}',
urgency='{classification.urgency.value}', sentiment='{classification.sentiment.value}'.
Ticket #{ticket.ticket_number} has been opened and assigned to {ticket.assigned_to or 'a technician'}.
Our first-response SLA for this urgency is {_humanize_minutes(sla.first_response_minutes)}.

{info_instruction}

Write in the customer's own language if it can be inferred from their message; otherwise English.
Match their emotional state with empathy - acknowledge frustration or urgency where present, stay
calm and competent, never sound like a form letter.

Fill in every field of the schema:
- `subject`: a short subject line referencing the ticket.
- `body`: the reply itself.
- `tone`: the tone you used (e.g. "empathetic", "reassuring", "professional").
- `language`: the language you wrote the reply in (ISO 639-1 code).
- `questions_asked`: the literal list of questions you asked the customer (empty if none).
- `includes_scheduling_link`: true only if the reply tells the customer someone will follow up to schedule a visit/call.
- `requires_human_review`: true if this situation is sensitive, high-stakes, or ambiguous enough that a human should check the reply before it goes out."""


def _build_user_content(message: NormalizedMessage, classification: Classification) -> str:
    return (
        f"Customer message:\n{message.body_text}\n\n"
        f"Classifier summary: {classification.summary}\n"
        f"Business impact: {classification.business_impact}"
    )


def _enforce_safety_net(draft: ReplyDraft, classification: Classification) -> ReplyDraft:
    """Deterministic guardrails on top of Gemini's own judgement - never trust the model alone for
    the things that decide whether a reply goes out unreviewed.
    """
    updates: dict = {}
    if len(draft.questions_asked) > _MAX_QUESTIONS:
        updates["questions_asked"] = draft.questions_asked[:_MAX_QUESTIONS]
    if (
        classification.confidence < _LOW_CONFIDENCE_THRESHOLD
        or classification.sentiment == Sentiment.ANGRY
    ) and not draft.requires_human_review:
        updates["requires_human_review"] = True
    return draft.model_copy(update=updates) if updates else draft


async def _maybe_send(
    message: NormalizedMessage, draft: ReplyDraft, *, correlation_id: str
) -> None:
    """Sends the reply automatically when AUTO_SEND_REPLIES is on, the channel supports it, and no
    human review was flagged. Best-effort: a send failure is logged, never raised - the draft
    still exists for manual dispatch either way.
    """
    if not settings.AUTO_SEND_REPLIES or draft.requires_human_review:
        return

    try:
        if message.channel == Channel.EMAIL and message.sender.email:
            client = get_gmail_client()
            await client.send_email(
                to=message.sender.email,
                subject=draft.subject,
                body_text=draft.body,
                correlation_id=correlation_id,
            )
        elif message.channel == Channel.SMS and message.sender.phone:
            client = get_twilio_client()
            await client.send_sms(to=message.sender.phone, body=draft.body, correlation_id=correlation_id)
    except IntegrationError as exc:
        log.warning("reply_agent_auto_send_failed", channel=message.channel.value, error=str(exc))


async def run(
    message: NormalizedMessage,
    classification: Classification,
    ticket: Ticket,
    *,
    vertical: VerticalConfig | None = None,
    correlation_id: str | None = None,
) -> ReplyDraft:
    """Drafts (and, if enabled, sends) the customer reply for a classified, ticketed message."""
    vertical = vertical or get_active_vertical()
    cid = correlation_id or message.intake_id

    async with timed_stage("reply_agent", correlation_id=cid, vertical=vertical.key):
        client = get_gemini_client()
        raw = await client.generate_structured(
            system_prompt=_build_system_prompt(vertical, classification, ticket),
            user_content=_build_user_content(message, classification),
            response_schema=ReplyDraft,
            correlation_id=cid,
        )
        draft = _enforce_safety_net(raw, classification)
        await _maybe_send(message, draft, correlation_id=cid)
        return draft
