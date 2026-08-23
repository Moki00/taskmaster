"""Simulation endpoint for the frontend dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.timing import timed_stage
from app.models import (
    Channel,
    NormalizedMessage,
    Sender,
    Sentiment,
    TicketDraft,
    Urgency,
)
from app.services.repository import get_repository
from app.verticals import get_active_vertical

router = APIRouter(prefix="/api", tags=["simulation"])


class SimulationRequest(BaseModel):
    client_name: str = Field(default="Alice Smith")
    message: str


class SimulationResponse(BaseModel):
    timestamp: str
    client: str
    category: str
    urgency: str
    device_type: str
    summary: str
    ticket_number: str
    logs: list[dict[str, str]]


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(payload: SimulationRequest) -> SimulationResponse:
    repo = get_repository()
    vertical = get_active_vertical()
    intake_id = f"intake-{uuid.uuid4().hex[:8]}"
    logs: list[dict[str, str]] = []

    # 1. Intake
    async with timed_stage("intake_agent", correlation_id=intake_id):
        norm_msg = NormalizedMessage(
            intake_id=intake_id,
            vertical=vertical.key,
            channel=Channel.WEB_FORM,
            sender=Sender(name=payload.client_name),
            body_text=payload.message,
        )
        logs.append({
            "id": "1",
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "text": f"Ingestion verified: Received payload from {payload.client_name}.",
            "status": "ok",
        })

    # 2. Heuristic / Agent Triage against active vertical
    async with timed_stage("classifier_agent", correlation_id=intake_id):
        msg_lower = payload.message.lower()
        
        # Match issue type against vertical pack
        issue_type = "other"
        for it in vertical.issue_types:
            if any(example.lower() in msg_lower for example in it.examples) or it.name in msg_lower:
                issue_type = it.name
                break
        if issue_type == "other" and vertical.issue_types:
            issue_type = vertical.issue_types[0].name

        urgency = Urgency.LOW
        if any(term in msg_lower for term in ["down", "dead", "emergency", "severe", "outage", "minutes"]):
            urgency = Urgency.CRITICAL
        elif any(term in msg_lower for term in ["broken", "flickering", "urgent"]):
            urgency = Urgency.HIGH

        detected_device = "Network / Gateway" if "switch" in msg_lower or "network" in msg_lower else "Workstation / Laptop"

        logs.append({
            "id": "2",
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "text": f"Classifier Agent: Category='{issue_type}', Urgency='{urgency.value}'.",
            "status": "ok",
        })

    # 3. Create Ticket
    async with timed_stage("ticket_agent", correlation_id=intake_id):
        ticket_draft = TicketDraft(
            intake_id=intake_id,
            vertical=vertical.key,
            customer=norm_msg.sender,
            issue_type=issue_type,
            priority=urgency,
            title=f"{issue_type.replace('_', ' ').title()} reported by {payload.client_name}",
            description=payload.message,
            extracted_details={"detected_device": detected_device},
            sentiment=Sentiment.ANNOYED if urgency in [Urgency.HIGH, Urgency.CRITICAL] else Sentiment.CALM,
            confidence=0.92,
            assigned_to=vertical.resolve_assignee(issue_type, urgency),
        )
        ticket = await repo.create_ticket(ticket_draft)
        logs.append({
            "id": "3",
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "text": f"Ticket Agent: Created CRM Ticket #{ticket.ticket_number} (Assigned to {ticket.assigned_to}).",
            "status": "ok",
        })

    logs.append({
        "id": "4",
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "text": "Reply Agent: Draft response queued for client acknowledgment.",
        "status": "ok",
    })

    return SimulationResponse(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        client=payload.client_name,
        category=issue_type.replace("_", " ").title(),
        urgency=f"{urgency.value.title()} Priority" if urgency != Urgency.CRITICAL else "Critical / High",
        device_type=detected_device,
        summary=payload.message,
        ticket_number=ticket.ticket_number,
        logs=logs,
    )