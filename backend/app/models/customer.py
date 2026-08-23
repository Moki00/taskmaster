"""Customer profile records, aggregated by the repository layer from ticket activity."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from app.models.base import TaskmasterModel


class Customer(TaskmasterModel):
    customer_id: str
    vertical: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ticket_count: int = Field(default=0, ge=0)
