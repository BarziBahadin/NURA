# NURA - Neural Unified Response Agent

NURA is an AI-assisted customer support system for telecom-style support teams.
It combines a self-contained chat widget, guided topic tree, retrieval-augmented AI answers, live human handoff, and admin reporting.

The system is designed for Arabic-first support, with Arabic, Kurdish, and English support in the widget, and can be embedded into any website with a single script tag.

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
Caddy Reverse Proxy (HTTPS termination)
  |  :8443 → FastAPI :8000
  |  :3443 → Admin Nginx :80
  |  :7443 → LiveKit :7880  (WSS for voice calls)
  |
  v
FastAPI Backend - port 8080 (HTTP) / 8443 (HTTPS via Caddy)
  |
  |-- Redis: session state and recent conversation history
  |-- PostgreSQL: logs, analytics, outcomes, feedback, reporting
  |-- ChromaDB: vector store for handbook retrieval
  |-- OpenAI: chat completion, embeddings, intent classification
  |-- Handoff Controller: escalation rules and agent routing
  |-- LiveKit: self-hosted WebRTC voice calls
  |
  v
React Admin Panel - port 3004 (HTTP) / 3443 (HTTPS via Caddy)
```

---

## Current Features

### Backend Hardening Status

Completed hardening and reliability work:

- Automated backend test suite for critical flows.
- Alembic database migrations plus local startup schema initialization.
- Durable PostgreSQL-backed sessions with Redis recovery.
- Redis-backed background job queue for important side effects.
- Postgres-first session and queue listing to avoid Redis full scans.
- Shared session access checks for widget/customer session endpoints.
- Telegram session reset handling after resolved sessions.
- Support cases, suggestions, SLA state, activity notes, and department routing.
- Admin user records, roles, JWT login, token revocation on user deactivation, and audit logging.
- Health checks, request IDs, runtime counters, worker heartbeats, and Docker health checks.

Still planned:

- Scheduled aggregation jobs when traffic grows.
- External metrics/error tooling such as Prometheus and Sentry.
- Production deployment profile split across API, worker, Telegram, and reverse proxy services.

### Chat Widget

- Embeddable `frontend/widget.js`, served by the API at `/widget.js`.
- Standalone local test page at `frontend/widget.html`.
- Arabic RTL, Kurdish Kurmanji, and English support.
- Lazy one-line loader at `/widget-loader.js`.
- Shadow DOM mounting when supported, with namespaced CSS fallback.
- Mobile-safe fullscreen behavior, safe-area handling, and focus trapping.
- Guided topic tree with instant article answers.
- Shared topic structure loaded from `/v1/topic-tree`; widget overlays Kurdish and English labels locally.
- Free-text chat through `/v1/message`.
- Per-answer confidence and source labels.
- Thumbs up/down feedback.
- Direct human-agent request button.
- Self-hosted voice-call request button powered by NURA's local LiveKit service.
- File/image upload after a session token exists.
- Suggestions and complaints form that creates back-office suggestion cases.
- Human handoff banner and live session continuation.

### AI And Knowledge

- OpenAI-backed response generation.
- RAG retrieval from ChromaDB using handbook chunks.
- Always-loaded article knowledge base from `.manafest/articals.json`.
- Prompt/context compression through `api/core/text_preprocessor.py`.
- Conversation memory from Redis.
- Async intent classification for reporting.
- LLM token usage and estimated cost logging.
- Admin toggle for OpenAI replies. When OpenAI replies are off, rules and local ML can still answer without sending customer text to OpenAI.
- Local ML training utilities under `training/` with curated/manual training pairs.

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

- **Dashboard**: operations command center for queue pressure, SLA risk, open cases, suggestions, attention items, trends, workload, and recent conversations.
- **Live Queue**: three-column pending/active handoff workflow, self-hosted voice-call requests, agent replies, canned responses, accept/resolve flow.
- **Cases**: support case tracking with owner, department, priority, SLA state, status, notes, and activity.
- **Suggestions**: dedicated queue for customer suggestions, complaints, recommendations, and general feedback.
- **Sessions**: conversation history search and review.
- **Reports**: deeper analytics tabs for knowledge gaps, intents, handoffs, outcomes, and cost.
- **Knowledge Gaps**: review/approve/reject/resolve gaps detected from weak answers and feedback.
- **Canned Replies**: reusable agent response snippets.
- **Knowledge Base**: handbook upload and ingestion controls.
- **Team**: admin user management with roles and activation state.
- **System Monitor**: realtime counters, live sessions, audit log, and operational activity.

Roles:

- `admin`: full access.
- `agent`: live queue, sessions, cases, suggestions, and agent workflows.
- `viewer`: read-only operations/reporting pages.

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
- `GET /v1/cases/stats`
- `GET /v1/suggestions/stats`
- `GET /v1/monitor/stats/realtime`

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
- counters for uploads, OpenAI calls, Telegram sends, suggestions, handoff accept time, and SLA transitions
- `/v1/health` checks for API, Redis, PostgreSQL, ChromaDB, uploads, ML artifacts, SLA monitor, job worker, and Telegram worker heartbeat
- `GET /v1/monitor/audit-log`
- `GET /v1/monitor/activity`

---

## Quick Start

Start from the project root:

```bash
cd /Users/barzy/code/NURA
```

Create `.env` if needed and set required secrets:

```bash
cp .env.example .env
```

At minimum, set:

- `POSTGRES_PASSWORD`
- `ADMIN_SECRET_KEY`
- `ADMIN_PASSWORD`
- `OPENAI_API_KEY` if OpenAI replies/RAG embeddings should run

### Fast Admin Development With Vite

For day-to-day UI work, use Vite instead of rebuilding the admin Docker image. Docker still runs the API, database, Redis, ChromaDB, LiveKit, and Caddy; Vite serves the React admin with hot reload.

```bash
./start-dev.sh
```

The script automatically:
- Detects your current LAN IP.
- Installs `mkcert` (via Homebrew) if not present.
- Generates trusted TLS certificates in `certs/` for `localhost`, `127.0.0.1`, and your LAN IP.
- Starts all Docker services including Caddy for HTTPS termination.
- Starts the Vite dev server.

Open the Vite admin:

```bash
open http://localhost:5173
```

HTTPS endpoints (require mkcert CA trusted on your machine):

```text
https://localhost:8443   API
https://localhost:3443   Admin
```

On another device on the same Wi-Fi, use the LAN URLs printed by `start-dev.sh`:

```text
https://YOUR-LAN-IP:8443/widget.html   Widget (HTTPS, required for microphone/voice)
https://YOUR-LAN-IP:3443               Admin panel
```

When running this way:

- React/admin changes update instantly.
- No Docker rebuild is needed for admin UI changes.
- API requests still go through `/v1` and are proxied to `http://localhost:8080`.
- HTTPS is required for microphone access in browsers — always use the `8443` URL for voice call testing.
- Keep using `http://localhost:3004` only for the production-style Nginx admin container.

### Docker Stack

Start the full production-style stack:

```bash
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

Check API health:

```bash
curl -X POST http://localhost:8080/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-admin-password"}'

curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8080/v1/health
```

Open the admin panel:

```bash
open http://localhost:3004
```

For active development, prefer `http://localhost:5173` from Vite.

Open the standalone widget:

```bash
open frontend/widget.html
```

Or test the hosted widget script:

```html
<script
  defer
  src="http://localhost:8080/widget-loader.js"
  data-api="http://localhost:8080/v1"
  data-lang="en"
  data-title="NURA">
</script>
```

Ingest handbook files into ChromaDB:

```bash
docker compose exec nura-api python /app/ingestion/ingest.py
```

Run backend tests:

```bash
docker compose exec nura-api pytest -q
```

Build the admin UI:

```bash
npm --prefix admin run build
```

---

## Services

| Service | URL | Notes |
|---|---|---|
| API (HTTP) | `http://localhost:8080` | FastAPI backend |
| API (HTTPS) | `https://localhost:8443` | Via Caddy, required for voice/mic |
| API Docs | `http://localhost:8080/docs` | Swagger UI |
| Health | `http://localhost:8080/v1/health` | Service checks |
| Widget (HTTP) | `http://localhost:8080/widget.html` | Test page, no mic/voice |
| Widget (HTTPS) | `https://localhost:8443/widget.html` | Full widget with mic/voice |
| Widget Script | `http://localhost:8080/widget.js` | Embeddable widget |
| Widget Loader | `http://localhost:8080/widget-loader.js` | Lazy one-line embed |
| Admin Panel (HTTP) | `http://localhost:3004` | React admin, Nginx container |
| Admin Panel (HTTPS) | `https://localhost:3443` | Via Caddy |
| Admin Dev (Vite) | `http://localhost:5173` | Hot-reload dev server |
| LiveKit (WS) | `ws://localhost:7880` | WebRTC signaling, HTTP only |
| LiveKit (WSS) | `wss://localhost:7443` | WebRTC signaling, via Caddy |
| ChromaDB | `http://localhost:8001` | Vector store |
| PostgreSQL | `127.0.0.1:5432` | Main reporting/logging DB |
| Redis | `127.0.0.1:6379` | Session cache |
| Worker | optional Compose profile | Redis-backed background jobs |
| Telegram Worker | optional Compose profile | Standalone Telegram polling |

---

## Health, Metrics, And Runtime Checks

Protected checks:

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8080/v1/health

curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8080/v1/metrics
```

The health endpoint reports:

- `postgres`, `redis`, and `chromadb`
- `uploads` directory write readiness
- `ml_model` artifact presence
- `sla_monitor` heartbeat
- `job_worker` heartbeat when background jobs are enabled
- `telegram_worker` heartbeat when Telegram polling is enabled

Docker Compose also has container health checks for the API, admin UI, standalone worker, and Telegram worker. If the Telegram worker is intentionally disabled, keep `TELEGRAM_POLLER_ENABLED=false` for the API process and do not start the `telegram` profile.

## Backup And Restore

Create a PostgreSQL backup:

```bash
mkdir -p backups
docker compose exec postgres pg_dump -U nura_user -d nura_db -Fc \
  > backups/nura_$(date +%Y%m%d_%H%M%S).dump
```

Restore PostgreSQL into the running database:

```bash
docker compose exec -T postgres pg_restore -U nura_user -d nura_db --clean --if-exists \
  < backups/nura_YYYYMMDD_HHMMSS.dump
```

Back up uploaded files:

```bash
tar -czf backups/uploads_$(date +%Y%m%d_%H%M%S).tar.gz uploads
```

Restore uploaded files:

```bash
tar -xzf backups/uploads_YYYYMMDD_HHMMSS.tar.gz
```

Back up ChromaDB data if you rely on persisted embeddings:

```bash
docker run --rm -v nura_nura_chroma_data:/data -v "$PWD/backups:/backup" alpine \
  tar -czf /backup/chroma_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

After a restore, restart the stack and verify:

```bash
docker compose up -d
curl -H "Authorization: Bearer <access_token>" http://localhost:8080/v1/health
```

---

## Embedding The Widget

```html
<script
  defer
  src="https://YOUR-SERVER/widget-loader.js"
  data-api="https://YOUR-SERVER/v1"
  data-lang="ar"
  data-position="bottom-left"
  data-primary="#f97316"
  data-accent="#22c55e"
  data-title="NURA">
</script>
```

The recommended embed uses the tiny lazy loader. It shows the launcher first and downloads the full widget only when the visitor opens chat. The full widget is self-contained, waits safely for `document.body`, mounts inside Shadow DOM when the browser supports it, and falls back to namespaced CSS on older browsers.

Supported embed options:

| Attribute | Values | Description |
|---|---|---|
| `data-api` | URL | API base URL, for example `https://YOUR-SERVER/v1` |
| `data-lang` | `ar`, `ku`, `en` | Initial widget language |
| `data-position` | `bottom-left`, `bottom-right` | Launcher position |
| `data-primary` | CSS color | Primary brand color |
| `data-accent` | CSS color | Accent color |
| `data-title` | Text | Header title shown in the widget |
| `data-widget-src` | URL | Optional full widget URL if it is not served beside `widget-loader.js` |

---

## API Examples

Most admin/back-office endpoints require a JWT:

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-admin-password"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

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

### Create A Suggestion

```bash
curl -X POST http://localhost:8080/v1/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "customer_id": "widget-xyz",
    "channel": "web",
    "kind": "suggestion",
    "message": "I suggest adding clearer package renewal reminders."
  }'
```

### Create A Case

```bash
curl -X POST http://localhost:8080/v1/cases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Customer cannot connect to internet",
    "description": "Customer reports no mobile data after APN reset.",
    "department": "technical",
    "priority": "high",
    "owner": "agent1"
  }'
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
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/v1/analytics/dashboard?days=30"
```

### Reports

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/v1/analytics/reports?days=30"
```

### Topic Tree

```bash
curl http://localhost:8080/v1/topic-tree
```

### AI Reply Toggle

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/v1/ai/status

curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/v1/ai/disable

curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/v1/ai/enable
```

### Resolve A Session

```bash
curl -X POST http://localhost:8080/v1/session/SESSION_ID/resolve \
  -H "Authorization: Bearer $TOKEN" \
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

PostgreSQL runs through Docker Compose and is exposed locally on `127.0.0.1:5432`.

Connection details:

```text
Type: PostgreSQL
Host: 127.0.0.1
Port: 5432
Database: nura_db
Username: nura_user
Password: value of POSTGRES_PASSWORD in .env
```

Recommended GUI clients:

- DBeaver
- TablePlus
- pgAdmin

MySQL Workbench is not suitable because this project uses PostgreSQL, not MySQL.

Important: run `docker compose ...` commands from the project root:

```bash
cd /Users/barzy/code/NURA
```

If you run Compose commands from another directory, Docker will fail with `no configuration file provided: not found`.

Open a Postgres shell:

```bash
docker compose exec postgres psql -U nura_user -d nura_db
```

Show all tables from inside `psql`:

```sql
\dt
```

Show all tables directly from the terminal:

```bash
docker compose exec postgres psql -U nura_user -d nura_db -c "\dt"
```

Show table names with estimated row counts:

```bash
docker compose exec postgres psql -U nura_user -d nura_db -c "
SELECT schemaname, relname AS table_name, n_live_tup AS estimated_rows
FROM pg_stat_user_tables
ORDER BY relname;
"
```

| Table | Purpose |
|---|---|
| `conversation_logs` | Customer and assistant messages, source, confidence, escalation state |
| `sessions` | Durable copy of live session state, history, metadata, and status |
| `tree_clicks` | Guided tree navigation and article usage |
| `widget_events` | Widget button clicks and telemetry |
| `message_feedback` | Good/bad response ratings |
| `message_insights` | LLM-classified intent, sentiment, confidence bucket, knowledge gaps |
| `knowledge_gap_reviews` | Admin review queue for detected knowledge gaps |
| `session_outcomes` | Handoff reason, status, category, root cause, resolution notes, timing |
| `llm_usage_logs` | Prompt tokens, completion tokens, total tokens, estimated cost |
| `chat_turns` | Live handoff conversation turns |
| `security_logs` | Auth failures and rate-limit events |
| `admin_audit_logs` | Admin auth and operational audit events |
| `admin_users` | Admin, agent, and viewer accounts |
| `ingestion_logs` | Handbook ingestion history |
| `support_departments` | Back-office department codes and names |
| `support_cases` | Cases, complaints, suggestions, SLA state, owner, department, priority |
| `support_case_activity` | Case activity feed and notes |
| `canned_replies` | Reusable agent response snippets |
| `daily_message_stats` | Aggregate message stats for reporting |
| `daily_cost_stats` | Aggregate OpenAI cost/token stats |
| `daily_handoff_stats` | Aggregate handoff stats |

Useful checks:

```bash
docker compose exec postgres psql -U nura_user -d nura_db \
  -c "SELECT session_id, customer_message, source, confidence, escalated, created_at FROM conversation_logs ORDER BY created_at DESC LIMIT 20;"
```

```bash
docker compose exec postgres psql -U nura_user -d nura_db \
  -c "SELECT event_type, COUNT(*) FROM widget_events GROUP BY event_type ORDER BY count DESC;"
```

```bash
docker compose exec postgres psql -U nura_user -d nura_db \
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
|-- Caddyfile              HTTPS reverse proxy config (API :8443, Admin :3443, LiveKit :7443)
|-- start-dev.sh           Dev launcher: auto-detects LAN IP, generates mkcert certs, starts Docker + Vite
|-- certs/                 Generated TLS certs (git-ignored, recreated by start-dev.sh)
|-- .env.example
|-- .manafest/
|   |-- articals.json
|   |-- system_prompt.txt
|   |-- topic_tree.json
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
|   |   |-- message_pipeline.py
|   |   |-- observability.py
|   |   |-- sla_monitor.py
|   |   |-- text_preprocessor.py
|   |   |-- logger.py
|   |-- routes/
|   |   |-- auth.py
|   |   |-- ai_control.py
|   |   |-- cases.py
|   |   |-- canned_replies.py
|   |   |-- message.py
|   |   |-- handoff.py
|   |   |-- session.py
|   |   |-- analytics.py
|   |   |-- health.py
|   |   |-- knowledge.py
|   |   |-- knowledge_gaps.py
|   |   |-- monitor.py
|   |   |-- upload.py
|   |   |-- users.py
|   |-- db/
|   |   |-- postgres.py
|   |   |-- migrations/
|   |-- workers/
|   |   |-- job_worker.py
|   |   |-- telegram_worker.py
|-- tests/
|   |-- conftest.py
|   |-- test_backend_phase1.py
|-- training/
|   |-- cli.py
|   |-- trainer.py
|   |-- evaluator.py
|   |-- processor.py
|   |-- data/
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
|   |   |   |-- Cases.jsx
|   |   |   |-- Suggestions.jsx
|   |   |   |-- Reports.jsx
|   |   |   |-- SessionViewer.jsx
|   |   |   |-- KnowledgeGapQueue.jsx
|   |   |   |-- CannedReplies.jsx
|   |   |   |-- KnowledgeBase.jsx
|   |   |   |-- UserManagement.jsx
|   |   |   |-- SystemMonitor.jsx
```

---

## Environment Variables

Copy `.env.example` to `.env` and set deployment-specific values.

| Variable | Description |
|---|---|
| `APP_ENV` | Runtime environment: development/staging/production |
| `COMPANY_NAME` | Company/support brand name injected into prompts |
| `AGENT_NAME` | Assistant name shown to users |
| `AGENT_TONE` | Tone hint for generated support replies |
| `PRIMARY_LANGUAGE` | Primary support language hint |
| `API_HOST` | API bind host inside the container |
| `API_PORT` | API bind port inside the container |
| `API_KEY` | Optional legacy bearer key for automation; disabled unless `ALLOW_ADMIN_API_KEY=true` |
| `ALLOW_ADMIN_API_KEY` | Permit `API_KEY` to access admin endpoints; keep `false` for browser-facing deployments |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model used for generated support replies |
| `OPENAI_EMBEDDING_MODEL` | Model used for RAG embeddings |
| `POSTGRES_HOST` / `POSTGRES_PORT` | PostgreSQL host and port from the API container |
| `POSTGRES_DB` / `POSTGRES_USER` | PostgreSQL database and username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_HOST` / `REDIS_PORT` | Redis host and port from the API container |
| `CHROMA_HOST` / `CHROMA_PORT` | ChromaDB host and port from the API container |
| `RAG_TOP_K` | Number of handbook chunks retrieved per query |
| `RAG_CHUNK_SIZE` | Chunk size for ingestion |
| `RAG_CHUNK_OVERLAP` | Chunk overlap for ingestion |
| `UNKNOWN_ANSWER_BEHAVIOR` | Behavior when confidence is low, for example `handoff` |
| `ML_MODEL_PATH` | Local ML model path inside the container |
| `ML_VECTORIZER_PATH` | Local ML vectorizer path inside the container |
| `ML_CONFIDENCE_THRESHOLD` | Minimum local ML confidence for using a local answer |
| `ML_REQUIRE_ARTIFACT_HASHES` | Require hashes in `models/metadata.json` before loading ML pickle artifacts |
| `USE_SEMANTIC_EMBEDDINGS` | Enable optional semantic embedding model for local ML utilities |
| `SEMANTIC_MODEL_NAME` | Sentence-transformers model name when semantic embeddings are enabled |
| `HANDOFF_ENABLED` | Enable or disable human handoff |
| `HANDOFF_TRIGGERS` | Comma-separated handoff trigger list |
| `ESCALATION_WEBHOOK_URL` | Optional webhook called when escalation is queued |
| `VOICE_CALL_ENABLED` | Enable or disable widget voice-call requests |
| `LIVEKIT_URL` | Browser-facing LiveKit websocket URL. Use `auto` for local/LAN development so the API returns a URL based on the current request host. When accessed via HTTPS, the API automatically returns `wss://hostname:7443` (via Caddy); when accessed via HTTP, it returns `ws://hostname:7880` |
| `LIVEKIT_NODE_IP` | LAN IP advertised by the local LiveKit container for WebRTC ICE candidates. Must match your machine's current LAN IP. Run `start-dev.sh` to auto-detect and regenerate certs when you change networks |
| `LIVEKIT_API_KEY` | LiveKit API key used by the backend to sign room tokens |
| `LIVEKIT_API_SECRET` | LiveKit API secret used by the backend to sign room tokens |
| `LIVEKIT_TOKEN_TTL_SECONDS` | Lifetime for generated voice-room tokens |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_POLLER_ENABLED` | Run Telegram polling in this process |
| `BACKGROUND_JOBS_ENABLED` | Enable Redis-backed background job enqueueing |
| `JOB_WORKER_ENABLED` | Run a background job worker in this process |
| `JOB_MAX_ATTEMPTS` | Max attempts before a job is moved to the failed queue |
| `JOB_RETRY_DELAY_SECONDS` | Delay between job retries |
| `ADMIN_SECRET_KEY` | Admin/session secret |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD` | Admin login password |
| `ADMIN_TOKEN_TTL_SECONDS` | Admin token lifetime |
| `DB_AUTO_INIT` | Run startup schema creation for local Docker/development |
| `CORS_ORIGINS` | Allowed browser origins |

---

## Recently Added

- HTTPS local development via mkcert and Caddy reverse proxy. `start-dev.sh` auto-detects LAN IP, installs mkcert, generates trusted certs, and starts Caddy for TLS termination on ports 8443 (API), 3443 (Admin), and 7443 (LiveKit WSS).
- LiveKit WSS support: voice signaling now uses `wss://hostname:7443` when accessed via HTTPS, routing through Caddy TLS termination. Required for browsers to allow microphone access on non-localhost addresses.
- Widget API base URL now derived from `window.location.origin` when not accessed directly on port 8080/8000, so tunnels (localhost.run, ngrok) and HTTPS proxy deployments work without hardcoded URLs.
- Secure context guard in the widget voice call path: shows a user-friendly error if microphone access is unavailable due to non-HTTPS context instead of crashing.
- Automated backend tests for message, handoff, resolve, analytics, reports, durable sessions, and job queue behavior.
- Alembic migrations with support cases, suggestions, activity notes, SLA state, admin users, and knowledge-gap reviews.
- Async LLM intent classification.
- Message insight logging for intents, sentiment, confidence bucket, and knowledge gaps.
- LLM token usage and estimated cost logging.
- Handoff reason tracking.
- Agent accept timestamp tracking.
- Durable PostgreSQL-backed session recovery.
- Postgres-backed session/queue listing to avoid Redis full scans.
- Telegram resolved-session reset so new conversations do not append forever to old resolved sessions.
- Detailed resolve outcomes: status, category, root cause, notes, resolver, timing.
- Operations-first dashboard with attention items, queue pressure, case SLA risk, suggestions, workload, and deltas.
- New `/v1/analytics/reports` endpoint.
- New admin Reports page with deep analytics tabs.
- Cases and Suggestions back-office workflows.
- Knowledge Gap review queue.
- Canned Replies editor.
- Team/user management UI.
- System Monitor page.
- Live Queue resolve modal with outcome fields.
- Self-hosted LiveKit voice-call MVP for widget-to-agent audio.
- Direct human-agent path that bypasses ML when the customer asks for an agent.
- Redis-backed background job queue for intent classification and escalation webhooks.
- Standalone Telegram worker option.
- Admin token login, `/auth/me`, roles, and JWT revocation on user deactivation.
- Request IDs, slow request logging, and `/v1/metrics`.
- Analytics hardening indexes and daily aggregate tables.
- Shared message pipeline for web and Telegram.
- Shared topic tree endpoint and widget translations for Arabic, Kurdish, and English.
- File/image uploads with session-token-protected access.

---

## Roadmap

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
- End-to-end browser tests for widget language switching, upload, suggestions, handoff, and live queue.
- More curated Arabic/Kurdish/English ML training data and regression evaluation gates.

---

## Production Checklist

- Set strong values for `POSTGRES_PASSWORD` and `ADMIN_SECRET_KEY`.
- Set a strong `ADMIN_PASSWORD` before first deployment.
- Keep `ALLOW_ADMIN_API_KEY=false` unless a trusted automation path explicitly needs it.
- Restrict `CORS_ORIGINS` to production domains.
- Move secrets out of plain `.env` for production deployments.
- Rotate any secret that was committed, pasted into logs, or shared in chat.
- Keep `POSTGRES_HOST=postgres`, `REDIS_HOST=redis`, and `CHROMA_HOST=chromadb` inside Docker Compose.
- Run only one Telegram poller. Use either API polling for local development or the `telegram` profile, not both.
- If using the standalone job worker, set `JOB_WORKER_ENABLED=false` on the API process and `true` on the worker.
- Rebuild API after Python changes: `docker compose build nura-api && docker compose up -d --force-recreate nura-api`.
- For voice calls to work from HTTPS, always access the widget via `https://` (port 8443 or 3443). Plain HTTP blocks microphone access in browsers.
- When your machine changes LAN IP (switching networks), update `LIVEKIT_NODE_IP` in `.env` and rerun `./start-dev.sh` to regenerate certs and restart containers.
- The `certs/` directory is git-ignored. Certs are regenerated on each `./start-dev.sh` run.
- During development, run the admin with Vite: `./start-dev.sh` or `npm --prefix admin run dev:host`.
- Rebuild admin after frontend changes only for production-style Docker/Nginx testing: `docker compose build nura-admin`.
- Restart after rebuilds: `docker compose up -d nura-api nura-admin`.
- Verify `/v1/health`, `/v1/analytics/dashboard`, and `/v1/analytics/reports`.
- Test widget embed with `data-lang="ar"`, `data-lang="ku"`, and `data-lang="en"`.
