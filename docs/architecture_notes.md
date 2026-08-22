# Taskmaster Architecture & Infrastructure Blueprint

Taskmaster is an autonomous, event-driven IT support triage and dispatch coordinator. It ingests inbound client communications (SMS, email, web forms), processes unstructured text with Gemini 3.5 Flash via the Google GenAI SDK and Google ADK (Agent Development Kit), and executes autonomous sub-task operations (ticketing, calendar scheduling, and draft replies).

---

## 1. System Architecture Flow

```

[ Inbound Client Request ] (Google Voice SMS / Gmail / Webhook)
│
▼
[ Cloud Pub/Sub Topic ] (gvoice-incoming-topic)
│
│ (Push Subscription)
▼
[ Cloud Run Webhook Engine ] (FastAPI Backend)
│
▼
[ Google ADK Router Agent ] (Gemini 3.5 Flash)
│
┌───────┴────────────────────────┬────────────────────────┐
▼ ▼ ▼
[ Tool: create_support_ticket ] [ Tool: check_schedule ] [ Tool: stage_sms_reply ]
│ │ │
▼ ▼ ▼
(Firestore / CRM Record) (Google Calendar Slot) (Draft Dispatch Queue)

```

---

## 2. Technology Stack

- **AI & Orchestration:** Google GenAI SDK (`google-genai`), Google ADK (`google-adk`), `gemini-3.5-flash`
- **Backend Runtime:** Python 3.11, FastAPI, Uvicorn, Pydantic v2
- **Cloud Infrastructure:** Google Cloud Run (containerized serverless backend), Cloud Pub/Sub (asynchronous event ingestion)
- **Frontend Dashboard:** React 18, Vite, Tailwind CSS, Lucide Icons

---

## 3. Google Cloud Setup & Configuration

Run these commands using the Google Cloud CLI (`gcloud`) to configure project resources:

### Step A: Enable Required Services

```bash
gcloud services enable \
    pubsub.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    generativelanguage.googleapis.com

```

### Step B: Create Pub/Sub Topic and IAM Bindings

```bash
# 1. Create the ingestion topic
gcloud pubsub topics create gvoice-incoming-topic

# 2. Allow Gmail Push Notifications to publish events
gcloud pubsub topics add-iam-policy-binding gvoice-incoming-topic \
    --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

```

### Step C: Deploy Backend to Cloud Run

```bash
# Deploy container from backend directory
gcloud run deploy taskmaster-backend \
    --source ./backend \
    --region us-east1 \
    --allow-unauthenticated \
    --set-env-vars GEMINI_API_KEY="your_api_key_here"

```

### Step D: Create Push Subscription to Cloud Run

```bash
gcloud pubsub subscriptions create gvoice-push-sub \
    --topic gvoice-incoming-topic \
    --push-endpoint https://<YOUR-CLOUD-RUN-URL>/webhook/pubsub

```

---

## 4. Agent Tool Definitions

The ADK triage agent (`backend/src/services/ai/tools.py`) dynamically triggers three autonomous tools based on user intent:

| Tool                            | Purpose                                                                             | Trigger Condition                                                    |
| ------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `create_support_ticket`         | Generates a structured CRM support ticket with urgency rating and category.         | Urgent outage, hardware failure, network issue.                      |
| `check_schedule_and_draft_slot` | Evaluates technician calendar availability and reserves a tentative support window. | Inquiries requesting appointments, consultations, or on-site visits. |
| `stage_sms_reply`               | Stages a contextual, professional acknowledgment response for client dispatch.      | All inbound requests requiring prompt client updates.                |

---

## 5. Environment Variables (`.env`)

```bash
# Google Cloud & AI Credentials
GEMINI_API_KEY="your_gemini_api_key"
GCP_PROJECT_ID="hackathon8-20"
GCP_REGION="us-east1"

# Pub/Sub Configuration
PUBSUB_TOPIC_NAME="gvoice-incoming-topic"
PUBSUB_SUBSCRIPTION_NAME="gvoice-push-sub"

# App Settings
PORT=8080
ENVIRONMENT="production"

```
