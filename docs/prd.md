# Product Requirements Document (PRD): Taskmaster

## 1. Product Overview

**Product Name:** Taskmaster

**Category:** Autonomous IT Support Operations & Triage Coordinator

**Core Purpose:** An autonomous, event-driven IT support dispatcher and workflow coordinator built for small MSPs and independent IT providers. Taskmaster transforms unstructured inbound customer communications (SMS, email, voice transcripts, web forms) into structured CRM tickets, automated calendar bookings, and contextual customer draft replies using **Gemini 3.5 Flash** on the Google Cloud Agent Platform.

---

## 2. Problem Statement

Solo IT technicians and small managed service providers face severe context-switching fatigue and operational friction:

- **Unstructured Inbound Chaos:** Critical network outages, hardware failures, and casual walk-ups arrive as messy text messages or emails without formal ticket numbers or severity tags.
- **Costly Diagnostic Lag:** Gathering initial diagnostic context (e.g., number of affected users, physical switch light states) requires manual back-and-forth messaging, delaying resolution.
- **Manual Operational Overhead:** Manually logging CRM tickets, checking technician availability, and dispatching acknowledgments creates a 15–30 minute operational lag per incident.

Taskmaster eliminates this friction by running an autonomous, multi-agent pipeline that ingests events in real time, classifies urgency, creates persistent Firestore records, prepares contextual replies with troubleshooting questions, and checks scheduling requirements in sub-two-second execution times.

---

## 3. User Personas

| Persona                      | Role      | Key Needs                                                                                                                               |
| ---------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Field Technician / MSP**   | Operator  | Instant incident categorization, zero manual ticket entry, automatic calendar protection during field work, transparent execution logs. |
| **End Customer / Requester** | Requester | Sub-minute acknowledgment, empathetic communication, step-by-step diagnostic triage questions during outages.                           |

---

## 4. Key Functional Requirements

### 4.1 Ingestion & Normalization

- **Event Ingestion:** Accept real-time push payloads via Google Cloud Pub/Sub from connected communication channels (Twilio SMS, Gmail API webhooks, web forms).
- **Live Simulator Endpoint:** Provide an authenticated `/api/simulate` endpoint for dashboard testing and live presentation demos.

### 4.2 Multi-Agent Autonomous Pipeline (Gemini 3.5 Flash via `google-genai`)

The backend orchestrates a 5-stage sequential agent pipeline using structured Pydantic schema validation:

1. **Intake Agent:** Parses raw unstructured payloads and extracts normalized customer metadata (`name`, `email`, `phone`, `company`, `body_text`).
2. **Classifier Agent:** Evaluates issue domain (`network`, `software`, `hardware`), sentiment, and urgency level (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with confidence scoring.
3. **Ticket Agent:** Atomically increments the vertical counter document in Cloud Firestore and generates durable tickets (e.g., `#TK-0046`) assigned to specific engineering roles.
4. **Reply Agent:** Synthesizes the customer's problem and drafts an empathetic acknowledgment containing targeted, diagnostic troubleshooting questions.
5. **Scheduler Agent:** Inspects technician calendar constraints and determines whether on-site consultation or dispatch is necessary.

### 4.3 Persistence & Storage Architecture

- **Cloud Firestore Collections:**
- `{prefix}_tickets`: Stores durable ticket documents (`it_support__TK-0046`), history entries, and metadata.
- `{prefix}_counters`: Maintains optimistic transactional counters per vertical (`value: 45`).
- `{prefix}_customers`: Automatically aggregates customer identity and repeat interaction history.
- `{prefix}_appointments`: Stores confirmed and proposed calendar slots.
- `{prefix}_processed_messages`: Enforces idempotent message processing to prevent duplicate tickets.

### 4.4 Visual Dispatcher Dashboard

- **Split-Screen Layout:** Interactive simulator on the left with preset outage/inquiry buttons and custom input forms; real-time automated execution trace on the right.
- **Live Status Feed:** Displays stage-by-stage timestamped logs with visual status badges, category tags, urgency indicators, and copyable customer draft replies.

---

## 5. Non-Functional & Technical Constraints

- **Inference & Execution Latency:** Target < 2.0 seconds end-to-end for the full 5-agent pipeline execution using `gemini-3.5-flash` on the `global` Agent Platform endpoint.
- **Security & Secret Management:** All API keys and sensitive tokens managed strictly through Google Secret Manager (`GEMINI_API_KEY:latest`).
- **Deployment Target:** Containerized serverless backend deployed on Google Cloud Run (`us-east1`) with scale-to-zero efficiency; frontend hosted on Firebase Hosting.
- **SDK Compliance:** Official Google GenAI SDK (`google-genai`) running in enterprise Vertex AI mode (`USE_VERTEXAI=true`, `USE_ENTERPRISE=true`).

---

## 6. Success Metrics & Validation

- **100% Schema Compliance:** Strict Pydantic model enforcement with zero unhandled JSON parsing failures.
- **Zero Data Loss & Strict Idempotency:** Atomic Firestore transaction guarantees for sequential ticketing (`#TK-xxxx`) across concurrent requests.
- **Human-in-the-Loop Safety:** Draft replies staged for operator verification before external dispatch when `AUTO_SEND_REPLIES=false`.
