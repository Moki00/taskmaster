# Taskmaster: Demo Flow & Presentation Script

This document outlines the step-by-step walkthrough and video presentation script for demonstrating Taskmaster's autonomous triage and dispatch capabilities.

---

## 1. Quick Video Script (3-Minute Hackathon Demo)

| Timestamp       | Video Screen                               | Narration Script                                                                                                                                                                                                                                                                                                                                                      |
| :-------------- | :----------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0:00 – 0:30** | Split-screen UI                            | _"Small IT providers face constant context switching: urgent text messages, panic emails, and calendar scheduling requests arriving simultaneously. Taskmaster is an autonomous event coordinator powered by Gemini 3.5 Flash and Google ADK that ingests messy communications and takes immediate operational action."_                                              |
| **0:30 – 1:15** | Client Simulator (Left Panel)              | _"Let's simulate an inbound emergency from a client: 'Our main switch is down and the office network is completely dead! Clients arrive in 20 minutes!' As we trigger this inbound payload, the backend receives the event via Cloud Pub/Sub and passes it to our ADK Router Agent."_                                                                                 |
| **1:15 – 2:00** | Extraction & Execution Trace (Right Panel) | _"Notice what happens instantly on the right: Gemini extracts structured metadata—marking Urgency as Critical and Categorizing it under Network Infrastructure. Simultaneously, the Agent triggers two autonomous tools: `create_support_ticket` to generate Ticket #1042 in our CRM, and `stage_sms_reply` with an immediate power-cycle checklist for the client."_ |
| **2:00 – 2:30** | Second Scenario (Consultation Request)     | _"Now let's test a non-urgent scenario: 'Looking to get a quote on setting up a new mesh Wi-Fi network.' The agent detects a low-urgency sales request, avoids emergency alerts, and automatically invokes `check_schedule_and_draft_slot` to propose calendar windows."_                                                                                             |
| **2:30 – 3:00** | Architecture / Cloud Run Overview          | _"Taskmaster runs containerized on Google Cloud Run, scaling to zero when idle, using the Google GenAI SDK for low-latency JSON schema enforcement. Thank you!"_                                                                                                                                                                                                      |

---

## 2. Test Scenarios for Reproducible Evaluation

### Scenario A: Critical Network Outage

- **Inbound Message:** `"Our main switch is down and the office network is completely dead! We have clients arriving in 20 minutes!"`
- **Expected Agent Output:**
  - **Category:** `Network / Infrastructure`
  - **Urgency:** `Critical / High`
  - **Triggered Tools:** `create_support_ticket(priority='High')`, `stage_sms_reply(...)`

### Scenario B: Routine Scheduling & Consultation

- **Inbound Message:** `"Hi Morgan, we are expanding our office next month and want to discuss setting up 10 new workstations. Can we meet Tuesday afternoon?"`
- **Expected Agent Output:**
  - **Category:** `Consultation / Deployment`
  - **Urgency:** `Standard Priority`
  - **Triggered Tools:** `check_schedule_and_draft_slot(preferred_time='Tuesday afternoon')`, `stage_sms_reply(...)`

### Scenario C: General Inquiry / Peripheral Support

- **Inbound Message:** `"My monitor is flickering intermittently after the Windows update. Any quick fix?"`
- **Expected Agent Output:**
  - **Category:** `Workstation / OS Support`
  - **Urgency:** `Low / Standard`
  - **Triggered Tools:** `stage_sms_reply(reply_body='Driver update & cable reseat checklist...')`

---

## 3. Local Live Demo Instructions

1. **Start Backend:**

   ```bash
   cd backend
   uvicorn src.main:app --reload --port 8000
   ```

2. **Start Frontend:**

   ```bash
   cd frontend
   npm run dev
   ```

3. Open `http://localhost:5173`, select any preset scenario on the left panel, and click **Simulate Incoming Request** to view real-time triage extraction and agent tool traces.
