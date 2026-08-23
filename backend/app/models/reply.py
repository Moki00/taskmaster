"""The output of the Reply Agent."""
from __future__ import annotations

from pydantic import Field

from app.models.base import TaskmasterModel


class ReplyDraft(TaskmasterModel):
    subject: str
    body: str
    tone: str
    language: str
    questions_asked: list[str] = Field(default_factory=list)
    includes_scheduling_link: bool = False
    requires_human_review: bool = False
