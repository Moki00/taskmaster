from pydantic import BaseModel, EmailStr
from typing import Optional, List

class InboundRequest(BaseModel):
    client_name: str
    client_email: EmailStr
    client_phone: Optional[str] = None
    raw_message: str

class ExtractedTicket(BaseModel):
    category: str              # e.g., "Network", "Hardware", "Software", "General"
    urgency: str               # "Critical", "Standard", "Low"
    device_type: Optional[str] # e.g., "Windows PC", "Router", "Printer"
    issue_summary: str
    suggested_troubleshooting_step: str
    auto_reply_message: str