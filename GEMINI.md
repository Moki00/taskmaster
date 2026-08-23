# Taskmaster — Project Context

Context file for the backend / AI pipeline owner. Read this at the start of every session before touching `backend/`.

Hackathon: **All Things Agentic Hackathon 2026** (Google + Devpost). Deadline: **Sunday Aug 30**.

## Team & Responsibilities

- **Morgan King** – Project Lead & Technical Architect
- **Dr. Agentic** – AI Core & Google ADK Agent Orchestration (`backend/src/services/ai/`)
- **Asmae** – FastAPI Routes & Cloud Pub/Sub Ingestion (`backend/src/api/`)
- **Ashvin** – Frontend Visualizer & React State Management (`frontend/src/`)
- **Habib Ur Rahman** – Ticket Persistence & External Integrations (`backend/src/services/`)

## Product

Taskmaster is an autonomous multi-agent system that turns messy, unstructured customer messages into clean, actionable tickets and booked appointments — **in under 30 seconds, with no human in the loop for standard requests.**

IT support / MSPs is the flagship vertical and the demo, but the architecture is **vertical-agnostic by design**. The same pipeline serves dental clinics, plumbing and home services, auto repair, salons, property management, law firms — any business that receives high volumes of inbound requests and books appointments.

What changes per vertical is **configuration** (taxonomy, urgency rules, tone, appointment types) — **never code**. "Add a new vertical" should be a config file someone writes in 20 minutes, not an engineering task.

## Channels

- Email (Gmail / Outlook)
- SMS (Twilio)
- Web form
- Slack
- **Voice** — customers can speak their problem instead of typing it. Voice is a first-class channel, not an afterthought.

## Architecture — 5-agent directed pipeline

Each agent passes state to the next.

1. **Intake Agent** — normalizes messages from every channel (including audio) into one internal schema; detects language; extracts sender name, email, phone, company; assigns `intake_id` + timestamp.
2. **Classifier Agent** — the core. Uses Gemini 3.5 for deep NLU of messy, incoherent, angry, multilingual, half-finished messages. Outputs `issue_type` and `urgency` from the **active vertical's taxonomy**, extracted entities, missing critical info, a customer sentiment/frustration read, and a calibrated confidence score.
3. **Ticket Agent** — builds the structured ticket, assigns number/priority/category/status, writes to Firestore, links customer history, routes to the right person.
4. **Reply Agent** — writes the customer reply, matching their language, tone, and emotional state. Complete info → confirmation + ticket number + expected response time. Missing info → at most 3 targeted questions. Never generic.
5. **Scheduler Agent** — decides if an appointment is needed, checks availability via native Google Calendar integration, proposes slots, confirms, blocks the slot, sets status to Scheduled.

## Why it matters (frames every design decision)

The product is not "ticket automation" — it is the difference between a frustrated customer waiting four hours for any sign of life, and that same customer getting an intelligent, specific, empathetic reply in under 30 seconds.

**Latency and empathy are the product.** Anything that adds seconds or reads like a robot is a bug.

## Stack

- Python 3.11, FastAPI (async)
- Google ADK for agent orchestration
- Gemini 3.5 for all LLM and audio understanding
- Google Firestore
- Native Google Calendar API
- Gmail API + Twilio (SMS and voice) for ingestion and sending
- Deployed on Google Cloud Run
- Frontend: React + Tailwind dashboard (teammate-owned; this repo owner provides the API it consumes)

## Engineering rules for this repo

- Python 3.11, full type hints, Pydantic v2 for every structure crossing a boundary.
- `async`/`await` everywhere; never block the event loop on an SDK call.
- No hardcoded secrets, model names, taxonomies, or business rules — config only.
- Nothing IT-specific hardcoded in agent code. IT support lives in a vertical config pack like every other vertical.
- Every LLM call returns validated structured JSON; never parse free text with regex.
- Every external call wrapped with timeout + retry + structured logging.
- Every agent stage logs elapsed time — the sub-30-second claim must be measurable.
- Small, focused modules. Ask before adding a dependency.

## Current repo state (as of clone)

The existing `backend/src/` is an early single-shot MVP (`ai_service.py` + `triage_agent.py` doing triage in one step, in-memory `tickets_db`, no vertical config). It predates the 5-agent / vertical-config architecture below. Treat it as a starting point to refactor toward the target structure, not as the target itself.

## Backend folder structure (target)

Target architecture for `backend/`, reflecting the 5-agent pipeline and vertical-agnostic config model above. Refactor toward this incrementally, don't big-bang rewrite.

```
backend/
├── Dockerfile
├── pyproject.toml
├── app/
│   ├── main.py                          # FastAPI app instantiation & route registration
│   ├── config.py                        # pydantic-settings: env vars, credentials, no literals elsewhere
│   │
│   ├── core/                            # cross-cutting infra, no business logic
│   │   ├── timing.py                    # timed_stage async context manager + in-memory event bus (built)
│   │   ├── retry.py                     # timeout + retry decorator/wrapper for all external calls
│   │   └── errors.py                    # shared exception types
│   │
│   ├── models/                          # Pydantic v2 models — the contract between all 5 agents (built)
│   │   ├── base.py                      # TaskmasterModel: shared config (extra="forbid", etc.)
│   │   ├── enums.py                     # Channel, Urgency, TicketStatus, Sentiment, AppointmentStatus
│   │   ├── common.py                    # Sender, Attachment, issue_type taxonomy validator
│   │   ├── message.py                   # NormalizedMessage (unified schema from all channels)
│   │   ├── classification.py            # Classification (issue_type, urgency, entities, confidence...)
│   │   ├── ticket.py                    # Ticket, TicketHistoryEntry (priority reuses Urgency)
│   │   ├── reply.py                     # ReplyDraft
│   │   ├── appointment.py               # Appointment, TimeSlot
│   │   └── pipeline.py                  # PipelineState, StageTiming, PipelineEvent, PipelineErrorEntry
│   │
│   ├── verticals/                       # THE config layer — "add a vertical" happens only here
│   │   ├── models.py                    # VerticalConfig pydantic schema (taxonomy, urgency rules, tone, appointment types)
│   │   ├── loader.py                    # loads/validates a vertical config pack by name
│   │   └── packs/
│   │       ├── it_support.yaml          # flagship/demo vertical
│   │       ├── dental_clinic.yaml
│   │       ├── plumbing.yaml
│   │       └── ...                      # each new vertical = one new file here, no code changes
│   │
│   ├── agents/                          # the 5-stage pipeline, Google ADK-orchestrated
│   │   ├── pipeline.py                  # wires the 5 agents, passes state, records stage timings
│   │   ├── intake_agent.py              # channel normalization, language detect, sender extraction
│   │   ├── classifier_agent.py          # Gemini 3.5 NLU against active vertical's taxonomy
│   │   ├── ticket_agent.py              # ticket construction, Firestore write, routing
│   │   ├── reply_agent.py               # tone/language-matched customer reply drafting
│   │   └── scheduler_agent.py           # appointment decision + Calendar booking
│   │
│   ├── channels/                        # per-channel ingestion adapters -> NormalizedMessage
│   │   ├── base.py                      # Channel interface/protocol
│   │   ├── email_gmail.py
│   │   ├── sms_twilio.py
│   │   ├── web_form.py
│   │   ├── slack.py
│   │   └── voice_twilio.py              # audio ingestion -> Gemini audio understanding
│   │
│   ├── integrations/                    # thin clients for external services, all async, timeout+retry
│   │   ├── gemini_client.py             # wraps Gemini 3.5 calls, enforces structured JSON output
│   │   ├── firestore_client.py
│   │   ├── calendar_client.py
│   │   ├── gmail_client.py
│   │   └── twilio_client.py
│   │
│   ├── services/                        # persistence layer (built)
│   │   ├── repository.py                # TicketRepository interface, get_repository(), TicketPage, errors
│   │   ├── firestore_repo.py            # FirestoreRepo: real Firestore, transactional ticket numbers
│   │   └── in_memory_repo.py            # InMemoryRepo: same interface, selected when ENV=local
│   │
│   └── api/
│       ├── deps.py                      # FastAPI dependency injection (settings, clients, active vertical)
│       └── routes/
│           ├── webhooks.py              # inbound push endpoints per channel
│           ├── tickets.py               # dashboard-facing endpoints (teammate's frontend consumes these)
│           └── simulate.py              # demo/live-testing endpoint
│
└── tests/
    ├── unit/
    │   ├── test_intake_agent.py
    │   ├── test_classifier_agent.py
    │   ├── test_ticket_agent.py
    │   ├── test_reply_agent.py
    │   └── test_scheduler_agent.py
    ├── integration/
    │   └── test_pipeline_end_to_end.py
    └── fixtures/
        └── sample_messages/              # messy/multilingual/angry sample inputs per vertical
```

### Structural rules this layout enforces

- **`verticals/`** is the only place taxonomy, urgency rules, tone, and appointment types may live. If an agent file references `"IT"`, `"printer"`, `"server down"`, or any other IT-specific literal, that's a bug — it belongs in `verticals/packs/it_support.yaml`. `models.classification.Classification.issue_type` and `models.ticket.Ticket.issue_type` enforce this at runtime via a Pydantic validation-context check (`validate_issue_type` in `models/common.py`) — no taxonomy data lives in `models/` itself.
- **`agents/`** files depend on `models/` and `verticals/`, never on a specific `channels/` or `integrations/` implementation directly — call through the client wrappers so external SDKs stay swappable and mockable in tests.
- **No agent touches the Firestore SDK directly.** Persistence goes through `services.repository.TicketRepository` (via `get_repository()`), never `FirestoreRepo`/`InMemoryRepo` by name — that's what lets the whole pipeline and its tests run with zero GCP credentials when `ENV=local`.
- **`channels/`** only normalizes into `models.message.NormalizedMessage`. No classification, ticketing, or reply logic belongs here.
- **`integrations/`** holds all timeout/retry/structured-logging wrapping (per the engineering rules above) so `agents/` code stays free of boilerplate.
- Every file under `agents/` logs its own elapsed time via `core/timing.py`'s `timed_stage` — this is what makes the sub-30-second claim measurable end to end.
- Every model in `models/` inherits `TaskmasterModel` (`extra="forbid"`) — a stray or typo'd field from an agent fails validation loudly instead of silently passing through to the next stage.
