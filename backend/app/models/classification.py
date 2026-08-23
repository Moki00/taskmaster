"""The output of the Classifier Agent."""
from __future__ import annotations

from typing import Any

from pydantic import Field, ValidationInfo, field_validator

from app.models.base import TaskmasterModel
from app.models.common import validate_issue_type
from app.models.enums import Sentiment, Urgency


class Classification(TaskmasterModel):
    issue_type: str
    urgency: Urgency
    summary: str
    extracted_details: dict[str, Any] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    sentiment: Sentiment
    frustration_score: float = Field(ge=0.0, le=1.0)
    business_impact: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    @field_validator("issue_type")
    @classmethod
    def _validate_issue_type(cls, v: str, info: ValidationInfo) -> str:
        return validate_issue_type(v, info)
