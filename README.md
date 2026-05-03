# NURA - Neural Unified Response Agent

NURA is an AI-assisted customer support system for telecom-style support teams.
It combines a self-contained chat widget, guided topic tree, retrieval-augmented AI answers, live human handoff, and admin reporting.

The system is designed for Arabic-first support, with Kurdish support in the widget, and can be embedded into any website with a single script tag.

---

## What It Does

- Answers common customer questions through an instant guided topic tree.
- Handles free-text messages through rules, local matching, RAG, and OpenAI.
- Escalates customers to a human agent when needed.
- Lets agents accept, chat with, and resolve customer sessions from the admin panel.
- Logs conversations, widget events, feedback, handoffs, LLM usage, and outcomes.
- Provides dashboard KPIs and a Reports page for operational review.

---

## Architecture

```text
Customer Website
  |
  |-- Embeddable widget.js or standalone frontend/widget.html
  |
  v
FastAPI Backend - port 8080
  |
  |-- Redis: session state and recent conversation history
  |-- PostgreSQL: logs, analytics, outcomes, feedback, reporting
  |-- ChromaDB: vector store for handbook retrieval
  |-- OpenAI: chat completion, embeddings, intent classification
  |-- Handoff Controller: escalation rules and agent routing
  |
  v
React Admin Panel - port 3004
```

---

## Current Features

### Backend Hardening Status

Completed hardening phases:

- Automated backend test suite for critical flows.
- Alembic database migrations.
- Durable PostgreSQL-backed sessions with Redis recovery.
- Redis-backed background job queue for important side effects.

Still planned:

- Full admin user-management UI.
- Scheduled aggregation jobs when traffic grows.
- External metrics/error tooling such as Prometheus and Sentry.
- Production deployment profile with API, worker, and Telegram split into separate processes.

### Chat Widget

- Embeddable `frontend/widget.js`, served by the API at `/widget.js`.
- Standalone local test page at `frontend/widget.html`.
- Arabic RTL and Kurdish Kurmanji support.
- Guided topic tree with instant article answers.
- Free-text chat through `/v1/message`.
- Per-answer confidence and source labels.
- Thumbs up/down feedback.
- Direct human-agent request button.
- Human handoff banner and live session continuation.

### AI And Knowledge

- OpenAI-backed response generation.
- RAG retrieval from ChromaDB using handbook chunks.
- Always-loaded article knowledge base from `.manafest/articals.json`.
- Prompt/context compression through `api/core/text_preprocessor.py`.
- Conversation memory from Redis.
- Async intent classification for reporting.
- LLM token usage and estimated cost logging.

### Human Handoff

Handoff can be triggered by:

- Explicit customer request for an agent.
- Negative or angry customer sentiment.
- Repeated low-confidence AI answers.
- Bad feedback from the widget.
- Direct widget handoff button.

When a handoff happens, the system stores the handoff reason. When an agent accepts a session, it stores `accepted_at`. When the session is resolved, the agent can record outcome fields.

### Session Durability

Redis remains the fast live session cache, but sessions are also persisted to PostgreSQL. If Redis misses a session, the backend attempts to restore it from the durable `sessions` table and writes it back into Redis.

Human handoff sessions get a longer Redis TTL than normal bot-only sessions so active support conversations are less likely to expire during follow-up.

### Admin Panel

The admin panel is built with React, Vite, and Tailwind.

Pages:

- **Dashboard**: KPIs, source breakdown, activity, latest conversations, satisfaction, deflection, resolution, knowledge gaps, and AI cost.
- **Live Queue**: pending handoffs, active chats, agent replies, canned responses, accept/resolve flow.
- **Reports**: five reporting tabs for knowledge gaps, intents, handoffs, outcomes, and cost.
- **Session Viewer**: conversation history search and review.
- **Knowledge Base**: handbook upload and ingestion controls.

### Reporting And Analytics

Tracked data includes:

- Conversation logs.
- Widget events.
- Guided tree clicks.
- Message feedback.
- Message intent insights.
- Knowledge gaps.
- LLM token usage and estimated cost.
- Session outcomes.
- Handoff reasons.
- Time to accept.
- Time to resolution.

Available reporting endpoints:

- `GET /v1/analytics/dashboard?days=30`
- `GET /v1/analytics/reports?days=30`
- `GET /v1/analytics/ratings`

### Background Jobs

Important side effects are sent through a Redis-backed job queue instead of raw fire-and-forget tasks.

Current queued jobs:

- intent classification
- escalation webhook delivery

The API runs a compatible background worker by default for local development. A standalone worker entrypoint also exists:

```bash
python -m workers.job_worker
```

Docker Compose includes an optional worker service behind the `workers` profile:

```bash
docker compose --profile workers up -d nura-worker
```

When running a dedicated worker in production, set `JOB_WORKER_ENABLED=false` for the API process and keep it enabled for the worker process.

### Telegram

Telegram can run inside the API process for local development, controlled by `TELEGRAM_POLLER_ENABLED`.

For production, run exactly one standalone Telegram worker:

```bash
docker compose --profile telegram up -d nura-telegram
```

Then set `TELEGRAM_POLLER_ENABLED=false` on the API service to avoid duplicate polling.

### Admin Auth And Observability

Admin endpoints still accept the internal API key for compatibility. A token login flow is also available:

- `POST /v1/auth/login`
- `GET /v1/auth/me`

Request observability includes:

- `X-Request-ID` response header
- slow request logging
- protected `GET /v1/metrics`

---

## Quick Start

```bash
docker compose up -d
```

Check API health:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/v1/health
```

Open the admin panel:

```bash
open http://localhost:3004
```

Open the standalone widget:

```bash
open frontend/widget.html
```

Ingest handbook files into ChromaDB:

```bash
docker compose exec nura-api python /app/ingestion/ingest.py
```

---

## Services

| Service | URL | Notes |
|---|---|---|
| API | `http://localhost:8080` | FastAPI backend |
| API Docs | `http://localhost:8080/docs` | Swagger UI |
| Health | `http://localhost:8080/v1/health` | Service checks |
| Widget Script | `http://localhost:8080/widget.js` | Embeddable widget |
| Admin Panel | `http://localhost:3004` | React admin |
| ChromaDB | `http://localhost:8001` | Vector store |
| PostgreSQL | `localhost:5432` | Main reporting/logging DB |
| Redis | `localhost:6379` | Session cache |
| Worker | optional Compose profile | Redis-backed background jobs |
| Telegram Worker | optional Compose profile | Standalone Telegram polling |

---

## Embedding The Widget

```html
<script
  src="http://YOUR-SERVER:8080/widget.js"
  data-api="http://YOUR-SERVER:8080/v1">
</script>
```

The widget is self-contained and injects its own namespaced CSS and DOM.

---

## API Examples

### Send A Message

```bash
curl -X POST http://localhost:8080/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "customer_id": "cust-001",
    "channel": "web",
    "message": "ما هي الباقات المتاحة؟"
  }'
```

Example response:

```json
{
  "session_id": "uuid",
  "response": "تم العثور على الإجابة المناسبة...",
  "channel": "web",
  "escalated": false,
  "confidence": 0.82,
  "source": "openai"
}
```

### Track Widget Event

```bash
curl -X POST http://localhost:8080/v1/analytics/click \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "customer_id": "widget-xyz",
    "event_type": "tree_click",
    "label": "الإنترنت بطيء",
    "meta": "slow",
    "topic_id": "slow",
    "article_id": 6
  }'
```

### Dashboard KPIs

```bash
curl "http://localhost:8080/v1/analytics/dashboard?days=30"
```

### Reports

```bash
curl "http://localhost:8080/v1/analytics/reports?days=30"
```

### Resolve A Session

```bash
curl -X POST http://localhost:8080/v1/session/SESSION_ID/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "status": "solved",
    "issue_category": "connectivity",
    "root_cause": "apn_settings",
    "resolution_notes": "Customer was guided through APN setup.",
    "resolved_by": "Agent"
  }'
```

---

## Database Tables

| Table | Purpose |
|---|---|
| `conversation_logs` | Customer and assistant messages, source, confidence, escalation state |
| `sessions` | Durable copy of live session state, history, metadata, and status |
| `tree_clicks` | Guided tree navigation and article usage |
| `widget_events` | Widget button clicks and telemetry |
| `message_feedback` | Good/bad response ratings |
| `message_insights` | LLM-classified intent, sentiment, confidence bucket, knowledge gaps |
| `session_outcomes` | Handoff reason, status, category, root cause, resolution notes, timing |
| `llm_usage_logs` | Prompt tokens, completion tokens, total tokens, estimated cost |
| `chat_turns` | Live handoff conversation turns |
| `security_logs` | Auth failures and rate-limit events |
| `ingestion_logs` | Handbook ingestion history |

Useful checks:

```bash
docker compose exec nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT session_id, customer_message, source, confidence, escalated, created_at FROM conversation_logs ORDER BY created_at DESC LIMIT 20;"
```

```bash
docker compose exec nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT event_type, COUNT(*) FROM widget_events GROUP BY event_type ORDER BY count DESC;"
```

```bash
docker compose exec nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT status, issue_category, handoff_reason, COUNT(*) FROM session_outcomes GROUP BY status, issue_category, handoff_reason;"
```

### Database Migrations

Alembic is configured under `api/db/migrations`.

Run migrations from inside the API container or an environment with the API dependencies installed:

```bash
cd /app
alembic -c alembic.ini upgrade head
```

For local Docker, the current app still keeps startup schema creation enabled by default through `DB_AUTO_INIT=true`. After a deployment is fully using Alembic, set `DB_AUTO_INIT=false` so startup only checks the database connection.

---

## Key Files

```text
NURA/
|-- docker-compose.yml
|-- .env.example
|-- .manafest/
|   |-- articals.json
|   |-- system_prompt.txt
|-- api/
|   |-- main.py
|   |-- config.py
|   |-- core/
|   |   |-- orchestrator.py
|   |   |-- rag_engine.py
|   |   |-- intent_classifier.py
|   |   |-- job_queue.py
|   |   |-- handoff_controller.py
|   |   |-- session_manager.py
|   |   |-- text_preprocessor.py
|   |   |-- logger.py
|   |-- routes/
|   |   |-- message.py
|   |   |-- handoff.py
|   |   |-- session.py
|   |   |-- analytics.py
|   |   |-- health.py
|   |-- db/
|   |   |-- postgres.py
|   |   |-- migrations/
|   |-- workers/
|   |   |-- job_worker.py
|-- tests/
|   |-- conftest.py
|   |-- test_backend_phase1.py
|-- ingestion/
|   |-- ingest.py
|   |-- handbook/
|   |-- knowledge/
|-- frontend/
|   |-- widget.js
|   |-- widget.html
|-- admin/
|   |-- src/
|   |   |-- App.jsx
|   |   |-- pages/
|   |   |   |-- Dashboard.jsx
|   |   |   |-- LiveQueue.jsx
|   |   |   |-- Reports.jsx
|   |   |   |-- SessionViewer.jsx
|   |   |   |-- KnowledgeBase.jsx
```

---

## Environment Variables

Copy `.env.example` to `.env` and set deployment-specific values.

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model used for generated support replies |
| `OPENAI_EMBEDDING_MODEL` | Model used for RAG embeddings |
| `COMPANY_NAME` | Company/support brand name injected into prompts |
| `AGENT_NAME` | Assistant name shown to users |
| `API_KEY` | Bearer key for internal/admin endpoints |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `ADMIN_SECRET_KEY` | Admin/session secret |
| `RAG_TOP_K` | Number of handbook chunks retrieved per query |
| `RAG_CHUNK_SIZE` | Chunk size for ingestion |
| `HANDOFF_ENABLED` | Enable or disable human handoff |
| `HANDOFF_TRIGGERS` | Comma-separated handoff trigger list |
| `TELEGRAM_POLLER_ENABLED` | Run Telegram polling in this process |
| `BACKGROUND_JOBS_ENABLED` | Enable Redis-backed background job enqueueing |
| `JOB_WORKER_ENABLED` | Run a background job worker in this process |
| `JOB_MAX_ATTEMPTS` | Max attempts before a job is moved to the failed queue |
| `JOB_RETRY_DELAY_SECONDS` | Delay between job retries |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD` | Admin login password |
| `ADMIN_TOKEN_TTL_SECONDS` | Admin token lifetime |
| `APP_ENV` | Runtime environment: development/staging/production |
| `CORS_ORIGINS` | Allowed browser origins |

---

## Recently Added

- Automated backend tests for message, handoff, resolve, analytics, reports, durable sessions, and job queue behavior.
- Alembic migrations with current schema through `20260430_002`.
- Async LLM intent classification.
- Message insight logging for intents, sentiment, confidence bucket, and knowledge gaps.
- LLM token usage and estimated cost logging.
- Handoff reason tracking.
- Agent accept timestamp tracking.
- Durable PostgreSQL-backed session recovery.
- Detailed resolve outcomes: status, category, root cause, notes, resolver, timing.
- Extended dashboard KPIs.
- New `/v1/analytics/reports` endpoint.
- New admin Reports page with five tabs.
- Live Queue resolve modal with outcome fields.
- Direct human-agent path that bypasses ML when the customer asks for an agent.
- Redis-backed background job queue for intent classification and escalation webhooks.
- Standalone Telegram worker option.
- Admin token login and `/auth/me`.
- Request IDs, slow request logging, and `/v1/metrics`.
- Analytics hardening indexes and daily aggregate tables.
- Shared message pipeline for web and Telegram.

---

## Roadmap

- Add full admin user-management UI and persistent admin user records.
- Add scheduled aggregate refresh jobs.
- Add external metrics/error tooling.
- Convert Telegram to webhook mode if long polling becomes operationally awkward.
- WhatsApp Business / Meta Cloud API channel adapter.
- CSV export from reports.
- More reporting filters by channel, agent, and issue category.
- Admin UI for editing article knowledge.
- Automatic ingestion after handbook upload.
- Better production deployment guide.
- Scheduled PostgreSQL and ChromaDB backups.
- Cached health checks so external model checks are not called too often.

---

## Production Checklist

- Set strong values for `API_KEY`, `POSTGRES_PASSWORD`, and `ADMIN_SECRET_KEY`.
- Restrict `CORS_ORIGINS` to production domains.
- Move secrets out of plain `.env` for production deployments.
- Rebuild API after Python changes: `docker compose build nura-api`.
- Rebuild admin after frontend changes: `docker compose build nura-admin`.
- Verify `/v1/health`, `/v1/analytics/dashboard`, and `/v1/analytics/reports`.
