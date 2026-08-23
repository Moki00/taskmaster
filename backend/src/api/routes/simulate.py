from fastapi import APIRouter
from pydantic import BaseModel
from src.services.ai.triage_agent import triage_agent

router = APIRouter()

class SimulationRequest(BaseModel):
    sender: str
    message: str

@router.post("/simulate")
async def run_simulation(payload: SimulationRequest):
    prompt = f"Inbound message from {payload.sender}: '{payload.message}'"
    result = await triage_agent.run_async(prompt)
    return {"status": "success", "result": str(result)}