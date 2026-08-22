# Product Requirements Document (PRD): Taskmaster

## 1. Product Overview

**Product Name:** Taskmaster  
**Category:** Taskmaster / Autonomous Operations Agent  
**Core Purpose:** An autonomous, event-driven IT support dispatcher and workflow coordinator built for small MSPs and independent tech support providers. Taskmaster transforms unstructured inbound communications (SMS, emails, webhooks) into structured CRM tickets, automated calendar bookings, and contextual client draft replies using Gemini 3.5 Flash and Google ADK.

---

## 2. Problem Statement

Solo IT technicians and small managed service providers face severe context-switching fatigue:

- Critical network outages arrive as chaotic, unstructured text messages.
- Non-urgent sales inquiries and scheduling requests interrupt high-focus diagnostic work.
- Manual ticket logging, calendar slot checks, and client updates create a 15–30 minute operational lag per incident.

Taskmaster solves this by running an autonomous, background triage agent loop that intercepts events in real time, classifies priority, and executes required tool operations before the technician even opens their laptop.

---

## 3. User Personas

| Persona                                 | Role              | Key Needs                                                                                                   |
| :-------------------------------------- | :---------------- | :---------------------------------------------------------------------------------------------------------- |
| **Lead Field Technician / MSP Founder** | Primary Operator  | Instant incident categorization, zero manual ticket entry, automatic calendar protection during field work. |
| **End Client / Customer**               | Inbound Requester | Immediate acknowledgment, step-by-step triage checklist during panic situations, transparent communication. |

---

## 4. Key Functional Requirements

### 4.1 Ingestion & Normalization

- Accept real-time push payloads via Google Cloud Pub/Sub from connected communication channels (e.g., forwarded Google Voice SMS, Gmail API webhooks).
- Provide a direct `/api/simulate` endpoint for local UI testing and presentation demos.

### 4.2 Autonomous AI Triage (Gemini 3.5 Flash & ADK)

- **Structured Extraction:** Extract structured JSON schema metadata:
  - `client_name`: Client or organization identity.
  - `category`: `Network / Infrastructure`, `Workstation / OS Support`, `Consultation / Deployment`, or `General Inquiry`.
  - `urgency`: `Critical / High`, `Medium`, or `Low / Standard`.
  - `summary`: Clean, 1–2 sentence technical synopsis.
- **Autonomous Tool Routing:** Based on message intent, the ADK agent dynamically invokes:
  1. `create_support_ticket`: Logs incident records into database/ticketing state.
  2. `check_schedule_and_draft_slot`: Evaluates technician schedule availability for consultation requests.
  3. `stage_sms_reply`: Generates a professional, contextual draft response.

### 4.3 Visual Dispatcher Dashboard

- **Split-Screen Layout:** Interactive simulator on the left with preset panic and routine inquiry buttons; real-time agent execution trace on the right.
- **Live Status Feed:** Displays execution step timestamps, status badges, and structured ticket parameters.

---

## 5. Non-Functional & Technical Constraints

- **Inference Latency:** Target < 1.5 seconds for complete agent reasoning and tool dispatch using `gemini-3.5-flash`.
- **Deployment Target:** Containerized deployment on Google Cloud Run with scale-to-zero capability to optimize infrastructure costs.
- **SDK Compliance:** Direct utilization of Google GenAI SDK (`google-genai`) and Google Agent Development Kit (`google-adk`).

---

## 6. Success Metrics for Hackathon Evaluation

- 100% schema enforcement compliance without JSON parsing errors.
- Dynamic multi-tool execution based on varying inbound prompt intent.
- Complete reproducible local setup in under 3 commands (`docker-compose up` or CLI startup).
