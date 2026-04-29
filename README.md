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
| `CORS_ORIGINS` | Allowed browser origins |

---

## Recently Added

- Async LLM intent classification.
- Message insight logging for intents, sentiment, confidence bucket, and knowledge gaps.
- LLM token usage and estimated cost logging.
- Handoff reason tracking.
- Agent accept timestamp tracking.
- Detailed resolve outcomes: status, category, root cause, notes, resolver, timing.
- Extended dashboard KPIs.
- New `/v1/analytics/reports` endpoint.
- New admin Reports page with five tabs.
- Live Queue resolve modal with outcome fields.
- Direct human-agent path that bypasses ML when the customer asks for an agent.

---

## Roadmap

- WhatsApp Business / Meta Cloud API channel adapter.
- Telegram bot channel adapter.
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
