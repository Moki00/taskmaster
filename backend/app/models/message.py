"""The output of the Intake Agent: one internal schema for messages from every channel."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from app.models.base import TaskmasterModel
from app.models.common import Attachment, Sender
from app.models.enums import Channel


class NormalizedMessage(TaskmasterModel):
    intake_id: str
    vertical: str
    channel: Channel
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sender: Sender
    subject: str | None = None
    body_text: str
    body_html: str | None = None
    language: str | None = None
    transcript: str | None = None
    audio_ref: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
