"""Fixed vocabularies shared across every vertical.

issue_type is deliberately NOT here — it is a vertical-defined taxonomy validated at
runtime (see models.common.validate_issue_type), never a hardcoded enum.
"""
from __future__ import annotations

from enum import Enum


class Channel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEB_FORM = "WEB_FORM"
    SLACK = "SLACK"
    VOICE = "VOICE"


class Urgency(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_ON_CUSTOMER = "WAITING_ON_CUSTOMER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Sentiment(str, Enum):
    CALM = "CALM"
    ANNOYED = "ANNOYED"
    FRUSTRATED = "FRUSTRATED"
    ANGRY = "ANGRY"


class AppointmentStatus(str, Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
