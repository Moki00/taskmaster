import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from .schemas import ExtractedTicket

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """
You are Taskmaster, an autonomous IT support dispatcher. 
Analyze the client's support message and extract key technical context.

Client Message: "{message}"
"""

def triage_message(raw_message: str) -> ExtractedTicket:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=PROMPT_TEMPLATE.format(message=raw_message),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedTicket,
            temperature=0.2,
        ),
    )
    data = json.loads(response.text)
    return ExtractedTicket(**data)