# Taskmaster Architecture & Infrastructure Blueprint

Taskmaster is an autonomous, event-driven IT support triage and dispatch coordinator. It ingests inbound customer communications (SMS, email, web forms), processes unstructured text with Gemini 3.5 Flash via the Google GenAI SDK on the Gemini Enterprise Agent Platform, and executes a coordinated 5-stage agent pipeline for classification, ticketing, customer replies, and scheduling.

---

## 1. System Architecture Flow

```powershell
[ Inbound Customer Request ] (Twilio SMS / Voice / Gmail / Webhook)
│
▼
[ Cloud Pub/Sub Ingestion ] (gvoice-incoming-topic)
│
│ (Push Subscription)
▼
[ Cloud Run Backend Engine ] (FastAPI / Python 3.11)
│
▼
[ 5-Stage Autonomous Agent Pipeline ] (Gemini 3.5 Flash via google-genai)
│
├── 1. Intake Agent ──> Normalizes transcripts and customer identity
├── 2. Classifier Agent ──> Categorizes domain & urgency (Low/Medium/High/Critical)
├── 3. Ticket Agent ──> Generates sequential ticket (#TK-0046) & assigns role
├── 4. Reply Agent ──> Drafts customer acknowledgment with targeted Qs
└── 5. Scheduler Agent ──> Validates calendar constraints & dispatch logic
│
▼
[ Cloud Firestore Persistence ] (Tickets, Customers, Counters, History)
```

---

## 2. Technology Stack

- **AI & Orchestration:** Google GenAI SDK (`google-genai`), `gemini-3.5-flash` on Gemini Enterprise Agent Platform
- **Backend Runtime:** Python 3.11, FastAPI, Uvicorn, Pydantic v2
- **Persistence & Cloud:** Google Cloud Run, Cloud Firestore, Cloud Pub/Sub, Google Secret Manager
- **Frontend Dashboard:** React 18, Vite, Tailwind CSS, Lucide Icons

---

## 3. Google Cloud Setup & Configuration

### Step A: Enable Required Services

```bash
gcloud services enable \
    pubsub.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    secretmanager.googleapis.com \
    firestore.googleapis.com \
    --project hackathon8-20

```

### Step B: Create Pub/Sub Topic and IAM Bindings

```bash
# 1. Create the ingestion topic
gcloud pubsub topics create gvoice-incoming-topic --project hackathon8-20

# 2. Allow push event publishing
gcloud pubsub topics add-iam-policy-binding gvoice-incoming-topic \
    --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
    --role="roles/pubsub.publisher" \
    --project hackathon8-20

```

### Step C: Deploy Backend to Cloud Run

```bash
cd ~/taskmaster/backend
gcloud run deploy taskmaster-backend \
    --source . \
    --region us-east1 \
    --project hackathon8-20 \
    --allow-unauthenticated \
    --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest \
    --set-env-vars ENV=production,ACTIVE_VERTICAL=it_support,GCP_PROJECT_ID=hackathon8-20,GCP_REGION=global,GEMINI_MODEL=gemini-3.5-flash,USE_ENTERPRISE=true,USE_VERTEXAI=true

```

### Step D: Create Push Subscription to Cloud Run

```bash
gcloud pubsub subscriptions create gvoice-push-sub \
    --topic gvoice-incoming-topic \
    --push-endpoint https://<YOUR-CLOUD-RUN-URL>/webhook/pubsub \
    --project hackathon8-20

```

---

## 4. Agent Pipeline Stage Responsibilities

| Agent Stage          | Core Responsibility                                                                          | Output Artifact        |
| -------------------- | -------------------------------------------------------------------------------------------- | ---------------------- |
| **Intake Agent**     | Ingests payload/transcripts, normalizes sender info and contact channels.                    | `IntakePayload`        |
| **Classifier Agent** | Evaluates technical domain, sentiment, and urgency rating with confidence scores.            | `ClassificationResult` |
| **Ticket Agent**     | Atomically fetches counter from Firestore, assigns technician roles, and creates `#TK-xxxx`. | `Ticket`               |
| **Reply Agent**      | Formulates a customer-facing draft acknowledgment with targeted diagnostic questions.        | `ReplyDraft`           |
| **Scheduler Agent**  | Inspects technician calendar windows and checks if on-site dispatch is necessary.            | `ScheduleResult`       |

---

## 5. Environment Configuration (`backend/.env`)

```bash
# Gemini & Agent Platform
GEMINI_API_KEY="AQ.Ab8..."
GEMINI_MODEL="gemini-3.5-flash"
USE_ENTERPRISE=true
USE_VERTEXAI=true

# Google Cloud & Firestore
GCP_PROJECT_ID="hackathon8-20"
GCP_REGION="global"
FIRESTORE_COLLECTION_PREFIX="taskmaster"

# Runtime & Vertical
ACTIVE_VERTICAL="it_support"
ENV="production"
PORT=8080

```
