from fastapi import FastAPI, HTTPException
from .schemas import InboundRequest, ExtractedTicket
from .ai_service import triage_message

app = FastAPI(title="Taskmaster API")

# In-memory store for MVP demo
tickets_db = []

@app.post("/api/inbound", response_model=ExtractedTicket)
async def handle_inbound_message(payload: InboundRequest):
    try:
        # 1. Run AI Triage
        parsed_ticket = triage_message(payload.raw_message)
        
        # 2. Store ticket (for dashboard)
        ticket_record = {
            "client_name": payload.client_name,
            "client_email": payload.client_email,
            "client_phone": payload.client_phone,
            **parsed_ticket.model_dump()
        }
        tickets_db.append(ticket_record)
        
        return parsed_ticket
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tickets")
async def list_tickets():
    return tickets_db