"""Small pieces shared across multiple models: contact info, attachments, issue_type validation."""
from __future__ import annotations

from pydantic import ValidationInfo

from app.models.base import TaskmasterModel


class Sender(TaskmasterModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None


class Attachment(TaskmasterModel):
    filename: str
    content_type: str
    url: str
    size_bytes: int | None = None


def validate_issue_type(v: str, info: ValidationInfo) -> str:
    """Validates issue_type against the active vertical's taxonomy, when supplied.

    The taxonomy itself lives in app/verticals config packs, not here. Callers that care about
    enforcement pass it in via Pydantic's validation context:

        Classification.model_validate(data, context={"valid_issue_types": vertical_config.issue_types})

    Without a context, only a basic non-empty check runs — this keeps the model usable before
    app/verticals exists, and keeps taxonomy data out of agent/model code entirely.
    """
    v = v.strip()
    if not v:
        raise ValueError("issue_type must not be empty")
    allowed = (info.context or {}).get("valid_issue_types") if info.context else None
    if allowed is not None and v not in allowed:
        raise ValueError(f"issue_type '{v}' is not in the active vertical's taxonomy: {sorted(allowed)}")
    return v
