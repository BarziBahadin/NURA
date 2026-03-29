# NURA — Neural Unified Response Agent
### Rcell Telecom · Internal AI Customer Support System

NURA is an Arabic-first AI customer service backend for Rcell Telecom.
It handles common support queries automatically, escalates to humans when needed,
and logs everything for analytics — powered by OpenAI GPT.

---

## Architecture

```
Customer (Web Widget)
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
        ├── PostgreSQL (conversation logs · port 5432)
        │
        └── Handoff Controller → Admin Panel (React · port 3004)
```

---

## What Is Built

### Core API (`/api`)
- FastAPI backend with Bearer token auth on all endpoints
- Rate limiting via slowapi (30 req/min per customer)
- CORS configured for local dev (ports 3000, 3001, 5173, 8080)

### Knowledge System (two layers)
- **Articles KB** — `.manafest/articals.json` — 20 articles loaded at startup and injected into every system prompt (no retrieval needed). Covers packages, apps, VoLTE, connectivity, passwords, showroom hours, SIM pricing.
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
- Configurable via `HANDOFF_TRIGGERS` in `.env`

### Conversation Logging (PostgreSQL)
- `conversation_logs` — every message: session, customer, channel, role, text, confidence, escalated flag, timestamp
- `security_logs` — auth failures and rate limit hits
- `ingestion_logs` — handbook ingestion history

### Admin Panel (`/admin`)
React + Vite + Tailwind, RTL Arabic UI on port 3004:
- **Dashboard** — system health, service statuses, active services count
- **Live Queue** — escalated sessions waiting for human agents
- **Session Viewer** — full history, searchable by customer/date/channel
- **Knowledge Base** — upload handbook files, trigger re-ingestion

### Test Frontend (`/frontend/index.html`)
Open directly in browser — no build step needed.
Shows live health status, session ID, confidence score per message.

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

# 4. Open the test chat
open frontend/index.html
```

---

## Services

| Service      | URL                                | Notes                       |
|--------------|------------------------------------|-----------------------------|
| API          | http://localhost:8080              | FastAPI backend             |
| API Docs     | http://localhost:8080/docs         | Swagger UI                  |
| Health Check | http://localhost:8080/v1/health    | All service statuses        |
| Admin Panel  | http://localhost:3004              | React dashboard             |
| ChromaDB     | http://localhost:8001              | Vector store (internal)     |
| Test Chat    | `frontend/index.html`              | Open directly in browser    |
| PostgreSQL   | localhost:5432                     | nura_user / NuraSecure2024! |
| Redis        | localhost:6379                     | Session cache               |

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
  "confidence": 0.196
}
```

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

Current articles (20 topics):
- Self-Care app: download, login issues, PIN activation
- Hakki app: download links
- Connectivity & APN troubleshooting
- Sending points between customers
- Slow internet — step-by-step fix guide
- HD Call (VoLTE) — what it is, activation (Android & iOS), troubleshooting
- Package pricing — الشمس، بلوتو، الأرض، القمر، المريخ، الكواكب (with SYP prices and point values)
- Showroom working hours
- SIM card availability and pricing (75,000 SYP)
- Password reset and recovery

### Handbook (RAG retrieval)
Place PDF/DOCX/TXT files in `ingestion/handbook/` then run:
```bash
docker exec nura-api python /app/ingestion/ingest.py
```
Currently ingested: call center handbook (8 chunks in ChromaDB).

---

## Token Cost Estimate

Context is sent to OpenAI on **every message**. Approximate breakdown per turn:

| Part | Tokens |
|------|--------|
| System prompt + rules | ~200 |
| Articles KB (compressed) | ~1,600 |
| RAG context (3 chunks) | ~300 |
| Conversation history (6 turns) | ~400 |
| User message | ~30 |
| **Total input per turn** | **~2,530** |
| Response output | ~200 |
| **Total per turn** | **~2,730** |

A 5-turn conversation ≈ 13,650 tokens. Check OpenAI dashboard for `gpt-5.4-nano` pricing.

---

## Database

```bash
# Open interactive shell
docker exec -it nura-postgres psql -U nura_user -d nura_db

# Recent conversations
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT session_id, customer_id, role, message, confidence, escalated, created_at FROM conversation_logs ORDER BY created_at DESC LIMIT 20;"

# Escalated sessions only
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT * FROM conversation_logs WHERE escalated = true;"

# Count total messages
docker exec -it nura-postgres psql -U nura_user -d nura_db \
  -c "SELECT COUNT(*) FROM conversation_logs;"
```

---

## Key Files

```
NURA/
├── .env                              ← all config & secrets (not in git)
├── docker-compose.yml                ← all services
├── .manafest/                        ← hidden folder, mounted into Docker
│   ├── articals.json                 ← 20 support articles (injected into every prompt)
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
│   │   └── sentiment.py              ← Arabic + English negative keyword scoring
│   ├── routes/
│   │   ├── message.py                ← POST /v1/message
│   │   └── health.py                 ← GET /v1/health (checks OpenAI, Redis, ChromaDB, Postgres)
│   └── db/
│       ├── postgres.py               ← DB pool + queries
│       └── migrations/001_init.sql
├── ingestion/
│   ├── ingest.py                     ← handbook PDF → ChromaDB (uses OpenAI embeddings)
│   └── handbook/                     ← place handbook files here (not in git)
├── frontend/
│   └── index.html                    ← test chat UI (open directly in browser)
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

### Analytics & Admin
- [ ] **Dashboard charts** — visual graphs for volume, escalation rate, top questions
- [ ] **Export conversations to CSV** — from the admin panel
- [ ] **Customer satisfaction rating** — post-session thumbs up/down
- [ ] **Admin panel login** — JWT auth so the panel is not open to everyone on the network

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
