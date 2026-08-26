"""Thin, async, timeout+retry+logged wrappers around every external service. Agents call these,
never the underlying SDKs directly. Every get_*_client() is a lazy singleton - importing this
package never requires credentials; only calling a factory that needs them does.
"""
from app.integrations.calendar_client import CalendarClient, get_calendar_client
from app.integrations.gemini_client import GeminiClient, get_gemini_client
from app.integrations.gmail_client import GmailClient, get_gmail_client
from app.integrations.twilio_client import TwilioClient, get_twilio_client

__all__ = [
    "CalendarClient",
    "GeminiClient",
    "GmailClient",
    "TwilioClient",
    "get_calendar_client",
    "get_gemini_client",
    "get_gmail_client",
    "get_twilio_client",
]
