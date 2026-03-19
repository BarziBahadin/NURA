# NURA — Neural Unified Response Agent
### [Your Company] · Internal AI Customer Support System

NURA is a fully local, Arabic-first AI customer service backend for [Your Company].
It replaces human call center agents for common support queries, escalates to humans when needed,
and logs everything for analytics — with zero cloud AI dependency.

---

## Architecture

```
Customer (Web Widget)
        │
        ▼
  FastAPI Backend (NURA API · port 8000)
        │
        ├── Redis · session memory (last 6 turns per conversation)
        │
        ├── RAG Engine
        │     ├── ChromaDB (vector store · port 8001 internal)
        │     └── nomic-embed-text via Ollama (embeddings)
        │
        ├── LLM: llama3.1:8b via Ollama
        │     └── SSH tunnel → remote server at 172.24.0.17:11434
        │
        ├── PostgreSQL (conversation logs · port 5432)
        │
        └── Handoff Controller → Admin Panel (React · port 3001)
```

---

## What Is Built

### Core API (`/api`)
- FastAPI backend with Bearer token auth on all endpoints
- Rate limiting via slowapi (30 req/min per customer)
- CORS configured for local dev (ports 3000, 3001, 5173, 8080)

### Knowledge System (two layers)
- **Articles KB** — `manafest/articals.json` loaded at startup and injected directly into every system prompt (always available, no retrieval needed). Covers 19 topics including packages, apps, VoLTE, connectivity, passwords, showroom hours, SIM pricing.
- **RAG Engine** — LlamaIndex + ChromaDB retrieves the top-3 most relevant handbook chunks per message using semantic search (nomic-embed-text embeddings)

### System Prompt
- Arabic formal tone, [Your Company] identity
- Strict guardrails: refuses off-topic questions, never invents information
- Greeting shown once by the frontend — LLM never repeats it
- Full rendered prompt available in `system_prompt.txt`

### Session Management
- Redis-backed sessions with full conversation history
- Last 6 turns injected into every LLM call for context

### Human Handoff
Escalation triggers (configurable in `.env`):
- Customer explicitly asks for a human / manager
- Angry sentiment detected (Arabic + English keyword scoring)
- AI fails to answer 2 consecutive times
- Confidence score too low

### Conversation Logging (PostgreSQL)
- `conversation_logs` — every message: session, customer, channel, role, text, confidence, escalated flag, timestamp
- `security_logs` — auth failures and rate limit hits
- `ingestion_logs` — handbook ingestion history

### Admin Panel (`/admin`)
React + Vite + Tailwind, RTL Arabic UI on port 3001:
- **Dashboard** — conversation stats and analytics
- **Live Queue** — escalated sessions waiting for human agents
- **Session Viewer** — full history, searchable by customer/date/channel
- **Knowledge Base** — upload handbook files, trigger re-ingestion

### Test Frontend (`/frontend/index.html`)
Open directly in browser — no build step needed.
Orange theme, Noto Sans Arabic font, RTL layout.
Shows live health status, session ID, confidence score per message.

---

## Prerequisites

- **OrbStack** (or Docker Desktop) running on Mac
- **SSH tunnel** to Ollama server open in a terminal:
  ```bash
  ssh -L 11434:localhost:11434 barzi@172.24.0.17 -N
  ```
- Models pulled on the remote server:
  - `llama3.1:8b` (LLM)
  - `nomic-embed-text` (embeddings)

---

## Quick Start

```bash
# 1. Open SSH tunnel (keep this terminal open)
ssh -L 11434:localhost:11434 barzi@172.24.0.17 -N

# 2. Start all services
docker compose up -d

# 3. Check everything is healthy
curl -H "Authorization: Bearer nura-dev-key-change-in-production" \
  http://localhost:8000/v1/health

# 4. Open the test chat
open frontend/index.html
```

---

## Services

| Service      | URL                               | Notes                       |
|--------------|-----------------------------------|-----------------------------|
| API          | http://localhost:8000             | FastAPI backend             |
| API Docs     | http://localhost:8000/docs        | Swagger UI                  |
| Health Check | http://localhost:8000/v1/health   | All service statuses        |
| Admin Panel  | http://localhost:3001             | React dashboard             |
| Test Chat    | `frontend/index.html`             | Open directly in browser    |
| PostgreSQL   | localhost:5432                    | nura_user / NuraSecure2024! |
| Redis        | localhost:6379                    | Session cache               |

---

## API Reference

### POST /v1/message
```bash
curl -X POST http://localhost:8000/v1/message \
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
  "response": "تفاصيل الباقات: ...",
  "channel": "web",
  "escalated": false,
  "confidence": 0.87
}
```

### GET /v1/health
```bash
curl -H "Authorization: Bearer nura-dev-key-change-in-production" \
  http://localhost:8000/v1/health
```

### POST /v1/knowledge/ingest
```bash
curl -X POST http://localhost:8000/v1/knowledge/ingest \
  -H "Authorization: Bearer nura-dev-key-change-in-production"
```

---

## Knowledge Base

### Articles (always in prompt)
Edit `manafest/articals.json` to add or update support articles. Restart the API after changes.

Current articles (19 topics):


### Handbook (RAG retrieval)
Place PDF/DOCX/TXT files in `ingestion/handbook/` then run:
```bash
docker exec nura-api python /app/ingestion/ingest.py
```

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
├── .env                          ← all config & secrets (not in git)
├── docker-compose.yml            ← all services
├── system_prompt.txt             ← full rendered system prompt for review
├── manafest/
│   └── articals.json             ← 19 support articles (injected into every prompt)
├── api/
│   ├── config.py                 ← loads all settings from .env
│   ├── main.py                   ← FastAPI app, CORS, rate limiting, lifespan
│   ├── core/
│   │   ├── orchestrator.py       ← system prompt builder + Ollama LLM call
│   │   ├── rag_engine.py         ← ChromaDB semantic retrieval
│   │   ├── session_manager.py    ← Redis session read/write
│   │   ├── handoff_controller.py ← escalation logic
│   │   └── sentiment.py          ← Arabic + English negative keyword scoring
│   ├── routes/
│   │   ├── message.py            ← POST /v1/message
│   │   └── health.py             ← GET /v1/health
│   └── db/
│       ├── postgres.py           ← DB pool + queries
│       └── migrations/001_init.sql
├── ingestion/
│   ├── ingest.py                 ← handbook PDF/DOCX → ChromaDB
│   └── handbook/                 ← place handbook files here (not in git)
├── frontend/
│   └── index.html                ← test chat UI (open directly in browser)
└── admin/
    └── src/App.jsx               ← React admin panel
```

---

## Environment Variables

| Variable | Current Value | Description |
|---|---|---|
| `LLM_MODEL` | `llama3.1:8b` | Ollama model for responses |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama via SSH tunnel |
| `API_KEY` | `nura-dev-key-change-in-production` | **Change before production** |
| `POSTGRES_PASSWORD` | `NuraSecure2024!` | **Change before production** |
| `ADMIN_SECRET_KEY` | `admin-secret-change-in-production` | **Change before production** |
| `RAG_TOP_K` | `3` | Chunks retrieved per query |
| `RAG_CHUNK_SIZE` | `512` | Token chunk size for ingestion |
| `UNKNOWN_ANSWER_BEHAVIOR` | `handoff` | What to do when AI has no answer |
| `HANDOFF_TRIGGERS` | `angry_sentiment,explicit_request,two_failures,keywords` | Escalation triggers |

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
- [ ] **Conversation summarization** — compress long sessions before they exceed LLM context window
- [ ] **Better Arabic sentiment** — replace keyword scoring with a small Arabic sentiment model

### Analytics & Admin
- [ ] **Dashboard charts** — visual graphs for volume, escalation rate, top questions
- [ ] **Export conversations to CSV** — from the admin panel
- [ ] **Customer satisfaction rating** — post-session thumbs up/down
- [ ] **Admin panel login** — JWT auth so the panel is not open to everyone on the network

### Infrastructure
- [ ] **Production deployment guide** — nginx, SSL, systemd SSH tunnel keepalive
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
- [ ] Set up a persistent SSH tunnel (autossh or systemd service)
- [ ] Move secrets to environment secrets manager (not plain `.env` file)
