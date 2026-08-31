### Taskmaster: Demo Flow & Video Recording Blueprint

This updated script aligns with the strict **Google Cloud proof requirement** (showing Cloud Run console, logs, or `.run.app` live endpoint), your actual **5-stage pipeline architecture**, and the real-world **IT owner walk-up / unscheduled request** hook.

---

### Video Timing & Stage Progression (Under 4:00 Target)

| Timestamp       | Video Focus                                                           | Narration & Action                                                                                                                                                                                                                                                                                                                                                                                         |
| --------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0:00 – 0:40** | **The Hook & Problem** (Slide / Camera)                               | _"As a small IT service provider, I constantly get walk-ups, urgent texts, and emails without a ticket. Someone walks up and says, 'Hey, can you fix this real quick?' That context-switching creates a 20-minute operational lag. We built Taskmaster: an autonomous event coordinator that converts unstructured requests into structured CRM tickets, calendar bookings, and diagnostic reply drafts."_ |
| **0:40 – 1:15** | **Architecture & Tech** (Blueprint Diagram)                           | _"Taskmaster runs on Google Cloud using Gemini 3.5 Flash via the Google GenAI SDK. Inbound events from SMS, email, or webhooks trigger our 5-agent pipeline on Cloud Run: Intake, Classifier, Ticket, Reply, and Scheduler—persisting all states to Cloud Firestore."_                                                                                                                                     |
| **1:15 – 2:30** | **Live Demo: Critical Outage** (Dashboard: `go-taskmaster-1.web.app`) | Click the **Panic / Network Outage** preset (_"Our primary switch is dead and office Wi-Fi dropped"_). Point out the live trace executing in sub-2 seconds: Classifier flags `network` / `CRITICAL`, Ticket Agent issues sequential Firestore ticket `#TK-0046`, and Reply Agent drafts a targeted questionnaire.                                                                                          |
| **2:30 – 3:15** | **Live Demo: Routine Inquiry & Calendar** (Dashboard)                 | Click the **Routine Inquiry** preset (_"Looking for a quote on a mesh Wi-Fi setup"_). Show how the Classifier downgrades priority, skips emergency escalations, and the Scheduler Agent evaluates calendar windows.                                                                                                                                                                                        |
| **3:15 – 3:45** | **Google Cloud Verification** (GCP Console / Cloud Run)               | **Mandatory:** Tab over to the Google Cloud Console showing the `taskmaster-backend` service in `hackathon8-20`, the `us-east1.run.app` service URL, and real-time container revision logs.                                                                                                                                                                                                                |
| **3:45 – 4:00** | **Value Proposition & Wrap-Up** (Closing Slide)                       | _"Taskmaster cuts initial response time from 30 minutes to under two seconds while maintaining human-in-the-loop safety controls. Built for MSPs and service businesses to stay organized and responsive."_                                                                                                                                                                                                |

---

### Checklist Before Uploading

- **Visibility Setting:** Must be set to **Public** on YouTube (never Unlisted or Private).
- **GCP Proof Included:** Ensure the Cloud Run dashboard, Cloud Shell, or GCP console is visibly displayed on screen for at least 15–30 seconds.
- **Audio Check:** Confirm voice audio is clean and background noise is minimal.
