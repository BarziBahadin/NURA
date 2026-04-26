# NURA — Neural Unified Response Agent
### Rcell Telecom · Internal AI Customer Support System

NURA is an Arabic-first AI customer service backend for Rcell Telecom.
It handles common support queries automatically via a guided decision tree and free-text AI, escalates to humans when needed, and logs everything for analytics — powered by OpenAI GPT.

---

## Architecture

```
Customer (Web Widget · frontend/widget.html)
        │
        ├── Guided Topic Tree (instant, zero-API answers from embedded articles)
        │
        ▼
  FastAPI Backend (NURA API · port 8080)
        │
        ├── Redis · session memory (last 6 turns per conversation)
        │
        ├── RAG Engine
        │     ├── ChromaDB (vector store · port 8001 external)
        │     └── text-embedding-3-small via OpenAI API
        │
        ├── LLM: gpt-5.4-nano-2026-03-17 via OpenAI API
        │
        ├── Text Preprocessor · token reduction on KB & RAG context
        │
        ├── PostgreSQL (conversation logs, analytics · port 5432)
        │
        └── Handoff Controller → Admin Panel (React · port 3004)
```

---

## What Is Built

### Core API (`/api`)
- FastAPI backend with Bearer token auth on all endpoints
- Rate limiting via slowapi (30 req/min per customer)
- CORS configured for local dev (ports 3000, 3001, 5173, 8080)

### Guided Decision Tree (Widget)
- 5 top-level categories → up to 3 levels deep → 25+ leaf nodes
- Leaf nodes answer instantly from embedded article content — **no API call, no latency**
- Answers tagged `source='rules'`, `confidence=0.97` and logged as normal conversations
- Back / Home navigation with breadcrumb trail
- Full Arabic + Kurdish (Kurmanji) bilingual support — tree labels, breadcrumbs, and all 29 article answers switch instantly when the language toggle changes
- Kurdish translations sourced from `ingestion/knowledge/Kurdish.md` and embedded into `ARTICLES_KU` in `widget.html`

### Knowledge System (two layers)
- **Articles KB** — `.manafest/articals.json` — **30 articles** loaded at startup and injected into every system prompt. Covers packages, apps, VoLTE, connectivity, passwords, showroom hours, SIM/eSIM, APN settings, Ana platform, 5G, business internet, Hakki emergency mode, recharge cards, data drain, PUK unlock.
- **RAG Engine** — LlamaIndex + ChromaDB retrieves the top-3 most relevant handbook chunks per message using OpenAI `text-embedding-3-small` embeddings.

### Token Preprocessor
- `api/core/text_preprocessor.py` — reduces prompt size before sending to OpenAI
- Articles KB is deduplicated + whitespace-compressed once at startup
- RAG context is whitespace-compressed per request
- Estimated 5–15% token savings on the system prompt

### System Prompt
- Arabic formal tone, Rcell Telecom identity
- Strict guardrails: refuses off-topic questions, never invents information
- If info is missing from KB: says so without promising a human transfer
- Greeting shown once by the frontend — LLM never repeats it
- Full rendered prompt in `.manafest/system_prompt.txt`

### Session Management
- Redis-backed sessions with full conversation history
- Last 6 turns injected into every LLM call for context

### Human Handoff
Escalation triggers (configurable in `.env`):
- Customer explicitly asks for a human / manager
- Angry sentiment detected (Arabic + English keyword scoring)
- AI fails to answer 2 consecutive times (confidence < 0.05)
- Thumbs-down feedback button in the widget
- Configurable via `HANDOFF_TRIGGERS` in `.env`

### Analytics System (`/api/routes/analytics.py`)

**Full button tracking** — every widget interaction is logged fire-and-forget:

| Event Type | Description |
|---|---|
| `chat_open` | Widget opened via toggle button |
| `chat_close` | Widget closed (toggle or close button) |
| `lang_switch` | Language changed (ar/ku) |
| `send_message` | Free-text message sent |
| `tree_click` | Guided tree topic or leaf selected |
| `tree_back` | Back button pressed in tree |
| `tree_home` | Home button pressed in tree |
| `followup_yes` | "Yes, I have another question" pressed |
| `followup_no` | "No, thanks" pressed |
| `feedback_good` | Thumbs-up feedback given |
| `feedback_bad` | Thumbs-down feedback given |

**Analytics Dashboard** (`frontend/dashboard.html`):
- KPI cards: sessions, messages, avg confidence, escalation rate, total tree clicks
- Donut chart: answer source breakdown (Rules / ML / AI / Escalated)
- Line chart: daily messages + sessions over time
- Bar chart: busiest hours (UTC, 24h distribution)
- Horizontal bar list: **all widget button interactions ranked by count**
- Horizontal bar list: top clicked guided tree topics
- Table: last 50 conversations with source badge and confidence score
- Period selector: 7 / 30 / 90 days; manual refresh button

### Conversation Logging (PostgreSQL)
- `conversation_logs` — every message: session, customer, channel, role, text, confidence, escalated flag, source, timestamp
- `tree_clicks` — every guided tree navigation event with topic/article info
- `widget_events` — every button press in the widget (event_type, label, meta)
- `security_logs` — auth failures and rate limit hits
- `ingestion_logs` — handbook ingestion history

### Chat Widget (`frontend/widget.html`)
- Bilingual: Arabic (RTL) and Kurdish Kurmanji (LTR), switchable mid-session
- Guided topic tree with instant inline answers
- Free-text input routed to the 3-tier API (Rules → ML → OpenAI)
- Per-message source badge (Rules / ML / AI) and confidence percentage
- Thumbs up/down feedback → bad feedback triggers human handoff
- Follow-up prompt after each answer
- Escalation banner when transferred to human agent
- Floating toggle button with notification badge

### Admin Panel (`/admin`)
React + Vite + Tailwind, RTL Arabic UI on port 3004:
- **Dashboard** — system health, service statuses, active services count
- **Live Queue** — escalated sessions waiting for human agents
- **Session Viewer** — full history, searchable by customer/date/channel
- **Knowledge Base** — upload handbook files, trigger re-ingestion

---

## Prerequisites

- **OrbStack** (or Docker Desktop) running on Mac
- **OpenAI API key** set in `.env`

No SSH tunnel or local GPU required — all AI runs through OpenAI API.

---

## Quick Start

```bash
# 1. Start all services
docker compose up -d

# 2. Check everything is healthy
curl -H "Authorization: Bearer nura-dev-key-change-in-production" \
  http://localhost:8080/v1/health

# 3. Ingest the handbook into ChromaDB (first time only, or after handbook changes)
docker exec nura-api python /app/ingestion/ingest.py

# 4. Open the chat widget
open frontend/widget.html

# 5. Open the analytics dashboard
open frontend/dashboard.html
```

---

## Services

| Service            | URL                                        | Notes                        |
|--------------------|--------------------------------------------|------------------------------|
| API                | http://localhost:8080                      | FastAPI backend               |
| API Docs           | http://localhost:8080/docs                 | Swagger UI                   |
| Health Check       | http://localhost:8080/v1/health            | All service statuses         |
| Analytics Dashboard| `frontend/dashboard.html`                  | Open directly in browser     |
| Chat Widget        | `frontend/widget.html`                     | Open directly in browser     |
| Admin Panel        | http://localhost:3004                      | React dashboard              |
| ChromaDB           | http://localhost:8001                      | Vector store (internal)      |
| PostgreSQL         | localhost:5432                             | nura_user / NuraSecure2024!  |
| Redis              | localhost:6379                             | Session cache                |

---

## API Reference

### POST /v1/message
```bash
curl -X POST http://localhost:8080/v1/message \
  -H "Authorization: Bearer nura-dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "customer_id": "cust-001",
    "channel": "web",
    "message": "ما هي باقات الإنترنت المتاحة؟"
  }'
```

Response:
```json
{
  "session_id": "uuid",
  "response": "أسعار باقات Rcell Telecom هي كالتالي...",
  "channel": "web",
  "escalated": false,
  "confidence": 0.196,
  "source": "openai"
}
```

### POST /v1/analytics/click
Tracks any widget interaction (fire-and-forget from the widget):
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

### GET /v1/analytics/dashboard
```bash
curl "http://localhost:8080/v1/analytics/dashboard?days=30"
```

Returns sessions, messages, confidence, escalation rate, source breakdown, top tree topics, daily volume, hourly distribution, event breakdown, and last 50 conversations.

### GET /v1/health
```bash
curl -H "Authorization: Bearer nura-dev-key-change-in-production" \
  http://localhost:8080/v1/health
```

### POST /v1/knowledge/ingest
```bash
curl -X POST http://localhost:8080/v1/knowledge/ingest \
  -H "Authorization: Bearer nura-dev-key-change-in-production"
```

---

## Knowledge Base

### Articles (always in prompt)
Edit `.manafest/articals.json` to add or update support articles. Restart the API after changes (`docker compose restart nura-api`).

Current articles (30 topics):
- Self-Care app: download, login issues, site access, PIN activation, password change/recovery
- Hakki app: download links, free emergency use
- Ana platform: unified login for all Rcell apps
- Connectivity: APN settings, no-connection troubleshooting
- Slow internet: 10-step fix guide
- Fast data drain: background app & update fixes
- HD Call (VoLTE): what it is, features, device support, activation (Android & iOS), usage, troubleshooting
- Packages: الشمس، بلوتو، الأرض، القمر، المريخ، الكواكب (SYP prices and point values)
- SIM card: availability and pricing (75,000 SYP)
- eSIM: digital SIM info and activation
- 5G: coming-soon announcement and readiness status
- Sending points between customers
- Scratched/damaged recharge cards
- PUK unlock procedure
- Showroom working hours
- Company coverage: 1,000+ towers, 40+ areas, 1.1M subscribers
- Business internet: FTTx fiber and 4G corporate plans

### Handbook (RAG retrieval)
Place PDF/DOCX/TXT files in `ingestion/handbook/` then run:
```bash
docker exec nura-api python /app/ingestion/ingest.py
```
Currently ingested: call center handbook (8 chunks in ChromaDB).

### Knowledge Reference Files (`ingestion/knowledge/`)
Static reference files used for content authoring and translation — not ingested into ChromaDB:

| File | Purpose |
|---|---|
| `Kurdish.md` | Kurdish (Kurmanji) translations of all 29 support articles — used to populate `ARTICLES_KU` in `widget.html` |
| `call center hand book ENG draft.pdf` | Source handbook (English) |
| `call center hand book in arabic.md` | Arabic call center knowledge base |
| `company_profile_ar.md` | Arabic company profile reference |
| `Rcell Company Profile 6.pdf` | Official company profile document |

### Arabic Content Reference (`nura_arabic_content.md`)
Project-root file with all Arabic rules-based content in one place: all tree navigation labels organized by category and all 29 article answer texts. Useful for auditing or translating content without reading `widget.html` directly.

---

## Database

```bash
# Open interactive shell
docker exec -it nura-postgres psql -U nura_user -d nura_db

# Recent conversations
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT session_id, customer_message, source, confidence, escalated, created_at FROM conversation_logs ORDER BY created_at DESC LIMIT 20;"

# Escalated sessions only
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT * FROM conversation_logs WHERE escalated = true;"

# Top widget events
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT event_type, COUNT(*) FROM widget_events GROUP BY event_type ORDER BY count DESC;"

# Top tree topics
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT topic_label, COUNT(*) AS clicks FROM tree_clicks GROUP BY topic_label ORDER BY clicks DESC LIMIT 10;"
```

### Tables

| Table | Purpose |
|---|---|
| `conversation_logs` | Every message: session, customer, channel, text, confidence, escalated, source |
| `widget_events` | Every button press: event_type, label, meta, session, customer |
| `tree_clicks` | Guided tree navigations with topic_id and article_id |
| `security_logs` | Auth failures and rate limit hits |

---

## Token Cost Estimate

Context is sent to OpenAI on **every free-text message** (tree answers use zero tokens):

| Part | Tokens |
|------|--------|
| System prompt + rules | ~200 |
| Articles KB (compressed) | ~2,200 |
| RAG context (3 chunks) | ~300 |
| Conversation history (6 turns) | ~400 |
| User message | ~30 |
| **Total input per turn** | **~3,130** |
| Response output | ~200 |
| **Total per turn** | **~3,330** |

A 5-turn conversation ≈ 16,650 tokens. Tree answers cost $0. Check OpenAI dashboard for `gpt-5.4-nano` pricing.

---

## Key Files

```
NURA/
├── .env                              ← all config & secrets (not in git)
├── docker-compose.yml                ← all services
├── nura_arabic_content.md            ← reference: all Arabic tree labels + article texts in one file
├── .manafest/                        ← hidden folder, mounted into Docker
│   ├── articals.json                 ← 30 support articles (injected into every prompt)
│   ├── call center hand book ENG draft.pdf  ← source for RAG ingestion
│   └── system_prompt.txt             ← rendered system prompt for review
├── api/
│   ├── config.py                     ← loads all settings from .env
│   ├── main.py                       ← FastAPI app, CORS, rate limiting, lifespan
│   ├── core/
│   │   ├── orchestrator.py           ← system prompt builder + OpenAI LLM call
│   │   ├── rag_engine.py             ← ChromaDB semantic retrieval (OpenAI embeddings)
│   │   ├── text_preprocessor.py      ← token reduction pipeline for KB & RAG context
│   │   ├── session_manager.py        ← Redis session read/write
│   │   ├── handoff_controller.py     ← escalation logic (threshold: confidence < 0.05)
│   │   ├── sentiment.py              ← Arabic + English negative keyword scoring
│   │   └── logger.py                 ← log_conversation, log_tree_click, log_widget_event, log_security_event
│   ├── routes/
│   │   ├── message.py                ← POST /v1/message
│   │   ├── analytics.py              ← POST /v1/analytics/click · GET /v1/analytics/dashboard
│   │   └── health.py                 ← GET /v1/health (checks OpenAI, Redis, ChromaDB, Postgres)
│   └── db/
│       ├── postgres.py               ← DB pool + init_db (creates all tables on startup)
│       └── migrations/001_init.sql
├── ingestion/
│   ├── ingest.py                     ← handbook PDF → ChromaDB (uses OpenAI embeddings)
│   ├── handbook/                     ← place handbook files here for RAG ingestion
│   └── knowledge/                    ← static reference files (not ingested)
│       ├── Kurdish.md                ← Kurdish translations of all 29 articles → ARTICLES_KU in widget.html
│       ├── call center hand book in arabic.md
│       ├── company_profile_ar.md
│       └── Rcell Company Profile 6.pdf
├── frontend/
│   ├── widget.html                   ← bilingual chat widget with guided tree + full button tracking
│   └── dashboard.html                ← analytics dashboard (open directly in browser)
└── admin/
    └── src/
        ├── App.jsx                   ← React admin panel + API config
        └── pages/
            ├── Dashboard.jsx         ← health + queue stats
            ├── Queue.jsx             ← live handoff queue
            └── Sessions.jsx          ← conversation viewer
```

---

## Environment Variables

| Variable | Current Value | Description |
|---|---|---|
| `OPENAI_API_KEY` | `sk-proj-...` | OpenAI API key |
| `OPENAI_MODEL` | `gpt-5.4-nano-2026-03-17` | LLM for responses |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings for RAG |
| `COMPANY_NAME` | `Rcell Telecom` | Injected into every system prompt |
| `AGENT_NAME` | `NURA` | Agent identity |
| `API_KEY` | `nura-dev-key-change-in-production` | **Change before production** |
| `POSTGRES_PASSWORD` | `NuraSecure2024!` | **Change before production** |
| `ADMIN_SECRET_KEY` | `admin-secret-change-in-production` | **Change before production** |
| `RAG_TOP_K` | `3` | Chunks retrieved per query |
| `RAG_CHUNK_SIZE` | `512` | Token chunk size for ingestion |
| `HANDOFF_ENABLED` | `true` | Enable/disable human handoff |
| `HANDOFF_TRIGGERS` | `angry_sentiment,explicit_request,two_failures,keywords` | Escalation triggers |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed origins |

---

## Planned Features & Future Improvements

### Channels
- [ ] **WhatsApp Business API** — connect to Meta Cloud API so customers chat via WhatsApp
- [ ] **Telegram Bot** — connect a bot token to receive and reply to messages
- [ ] **Mobile App REST** — same API already works, just needs auth token distribution

### Knowledge & AI
- [ ] **Admin UI to edit articles** — edit `articals.json` from the admin panel without touching files
- [ ] **Auto-ingest on handbook upload** — trigger ChromaDB ingestion automatically on file upload
- [ ] **Confidence threshold tuning** — adjustable in admin panel
- [ ] **Better Arabic sentiment** — replace keyword scoring with a small Arabic sentiment model
- [ ] **Expand guided tree** — add more leaf nodes as new articles are added

### Analytics & Admin
- [x] **Analytics dashboard** — KPIs, charts for volume, escalation rate, top topics (done: `dashboard.html`)
- [x] **Full button tracking** — every widget interaction logged to `widget_events` (done)
- [x] **Customer satisfaction rating** — thumbs up/down per bot response (done)
- [ ] **Export conversations to CSV** — from the admin panel
- [ ] **Admin panel login** — JWT auth so the panel is not open to everyone on the network
- [ ] **Real-time dashboard** — WebSocket push instead of manual refresh

### Infrastructure
- [ ] **Production deployment guide** — nginx, SSL, domain setup
- [ ] **`.env.example`** — safe template with no real secrets for new deployments
- [ ] **Automated backups** — PostgreSQL + ChromaDB to local file on schedule
- [ ] **Docker healthcheck for nura-api** — proper startup dependency ordering

---

## Production Checklist

Before going live, update these in `.env`:
- [ ] `API_KEY` — generate a strong random key
- [ ] `POSTGRES_PASSWORD` — use a strong password
- [ ] `ADMIN_SECRET_KEY` — generate a strong random key
- [ ] `CORS_ORIGINS` — restrict to your actual production domain
- [ ] Move secrets to environment secrets manager (not plain `.env` file)
- [ ] Rebuild Docker image after any Python file changes: `docker compose build nura-api`
