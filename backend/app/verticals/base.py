"""VerticalConfig: the schema every business-vertical config pack must satisfy.

This is THE config layer (GEMINI.md): taxonomy, urgency rules, tone, appointment types, SLAs, and
routing all live here as data, never as code in app/agents/*.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from app.models.base import TaskmasterModel
from app.models.enums import Urgency


class IssueType(TaskmasterModel):
    name: str
    description: str
    examples: list[str] = Field(default_factory=list)


class UrgencyRule(TaskmasterModel):
    level: Urgency
    definition: str
    concrete_examples: list[str] = Field(default_factory=list)


class RequiredEntity(TaskmasterModel):
    name: str
    description: str


class AppointmentType(TaskmasterModel):
    name: str
    duration_minutes: int = Field(gt=0)
    requires_onsite: bool
    triggers_when: str


class DayHours(TaskmasterModel):
    open: str | None = None
    close: str | None = None

    @field_validator("open", "close")
    @classmethod
    def _validate_time_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as exc:
            raise ValueError(f"'{v}' is not a valid 24h HH:MM time") from exc
        return v

    @model_validator(mode="after")
    def _check_both_or_neither(self) -> "DayHours":
        if (self.open is None) != (self.close is None):
            raise ValueError("open and close must both be set, or both be null (closed)")
        return self


class BusinessHours(TaskmasterModel):
    monday: DayHours
    tuesday: DayHours
    wednesday: DayHours
    thursday: DayHours
    friday: DayHours
    saturday: DayHours
    sunday: DayHours


class SlaTarget(TaskmasterModel):
    first_response_minutes: int = Field(gt=0)
    resolution_hours: float | None = Field(default=None, gt=0)


class RoutingRule(TaskmasterModel):
    issue_type: str
    urgency: Urgency | None = None  # None = wildcard, matches any urgency for this issue_type
    assignee_role: str


class VerticalConfig(TaskmasterModel):
    key: str
    display_name: str
    business_description: str
    issue_types: list[IssueType] = Field(min_length=1)
    urgency_rules: list[UrgencyRule] = Field(min_length=1)
    required_entities: list[RequiredEntity] = Field(default_factory=list)
    appointment_types: list[AppointmentType] = Field(default_factory=list)
    reply_tone: str
    business_hours: BusinessHours
    timezone: str
    sla_by_priority: dict[Urgency, SlaTarget]
    routing_table: list[RoutingRule] = Field(default_factory=list)
    default_assignee_role: str

    @field_validator("key")
    @classmethod
    def _validate_key(cls, v: str) -> str:
        v = v.strip()
        if not v or " " in v or v != v.lower():
            raise ValueError(f"key must be a non-empty lowercase slug with no spaces, got '{v}'")
        return v

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"'{v}' is not a valid IANA timezone name") from exc
        return v

    @model_validator(mode="after")
    def _check_issue_type_names_unique(self) -> "VerticalConfig":
        names = [it.name for it in self.issue_types]
        if len(names) != len(set(names)):
            raise ValueError(f"issue_types names must be unique, got duplicates in: {names}")
        return self

    @model_validator(mode="after")
    def _check_urgency_rules_cover_all_levels(self) -> "VerticalConfig":
        levels = {rule.level for rule in self.urgency_rules}
        if levels != set(Urgency):
            raise ValueError(
                f"urgency_rules must cover exactly all Urgency levels {sorted(Urgency)}, got {sorted(levels)}"
            )
        return self

    @model_validator(mode="after")
    def _check_sla_covers_all_levels(self) -> "VerticalConfig":
        levels = set(self.sla_by_priority)
        if levels != set(Urgency):
            raise ValueError(
                f"sla_by_priority must cover exactly all Urgency levels {sorted(Urgency)}, got {sorted(levels)}"
            )
        return self

    @model_validator(mode="after")
    def _check_routing_table_issue_types_exist(self) -> "VerticalConfig":
        valid_names = {it.name for it in self.issue_types}
        for rule in self.routing_table:
            if rule.issue_type not in valid_names:
                raise ValueError(
                    f"routing_table references unknown issue_type '{rule.issue_type}', "
                    f"expected one of {sorted(valid_names)}"
                )
        return self

    @property
    def issue_type_names(self) -> set[str]:
        """The exact collection to pass as context={"valid_issue_types": ...} to Classification/Ticket."""
        return {it.name for it in self.issue_types}

    def resolve_assignee(self, issue_type: str, urgency: Urgency) -> str:
        """Exact (issue_type, urgency) match, then issue_type wildcard, then the vertical's default."""
        for rule in self.routing_table:
            if rule.issue_type == issue_type and rule.urgency == urgency:
                return rule.assignee_role
        for rule in self.routing_table:
            if rule.issue_type == issue_type and rule.urgency is None:
                return rule.assignee_role
        return self.default_assignee_role
