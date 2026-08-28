"""Ticket Agent: turns a Classification into a persisted, routed Ticket - the durable record of
the interaction. Routing (who gets assigned) and repeat-contact detection are handled entirely by
the vertical config and the repository layer respectively; this agent just wires them together.
"""
from __future__ import annotations

from app.core.timing import timed_stage
from app.models.classification import Classification
from app.models.message import NormalizedMessage
from app.models.ticket import Ticket, TicketDraft
from app.services.repository import get_repository
from app.verticals.base import VerticalConfig
from app.verticals.loader import get_active_vertical


def _build_title(classification: Classification, message: NormalizedMessage) -> str:
    who = message.sender.name or message.sender.company or "customer"
    label = classification.issue_type.replace("_", " ").title()
    return f"{label} - {who}"


async def run(
    message: NormalizedMessage,
    classification: Classification,
    *,
    vertical: VerticalConfig | None = None,
    correlation_id: str | None = None,
) -> Ticket:
    """Builds a TicketDraft from the message + its classification, resolves the assignee via the
    vertical's routing table, and persists it through TicketRepository.
    """
    vertical = vertical or get_active_vertical()
    cid = correlation_id or message.intake_id

    async with timed_stage("ticket_agent", correlation_id=cid, vertical=vertical.key):
        assigned_to = vertical.resolve_assignee(classification.issue_type, classification.urgency)

        draft = TicketDraft.model_validate(
            {
                "intake_id": message.intake_id,
                "vertical": vertical.key,
                "customer": message.sender,
                "issue_type": classification.issue_type,
                "priority": classification.urgency,
                "title": _build_title(classification, message),
                "description": message.body_text,
                "extracted_details": classification.extracted_details,
                "missing_info": classification.missing_info,
                "sentiment": classification.sentiment,
                "confidence": classification.confidence,
                "assigned_to": assigned_to,
            },
            context={"valid_issue_types": vertical.issue_type_names},
        )

        repo = get_repository()
        return await repo.create_ticket(draft)
