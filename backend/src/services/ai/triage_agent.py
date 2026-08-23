"""
Google ADK Agent Initializer for Taskmaster.
"""
import os
from google.adk.agents import Agent
from src.services.ai.tools import (
    create_support_ticket,
    check_schedule_and_draft_slot,
    stage_sms_reply,
)

triage_agent = Agent(
    name="taskmaster_triage_agent",
    model="gemini-3.5-flash",
    instruction="""
    You are an autonomous Taskmaster agent handling inbound IT requests.
    Analyze the incoming message body and sender context:
    1. If the message reports an urgent technical/system issue: Call `create_support_ticket` with priority='High' and draft an acknowledgment via `stage_sms_reply`.
    2. If the message requests a meeting, call, or quote: Call `check_schedule_and_draft_slot`.
    3. For general inquiries: Generate a helpful, concise response and stage it with `stage_sms_reply`.
    Always execute the required tool calls autonomously based on message intent.
    """,
    tools=[create_support_ticket, check_schedule_and_draft_slot, stage_sms_reply]
)