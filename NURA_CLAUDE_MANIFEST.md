# 🤖 NURA — Neural Unified Response Agent
## Claude Code Project Manifest v1.0

> **What this file is:** A complete build manifest for Claude Code.
> Read this entire file first, then follow the INSTRUCTIONS FOR CLAUDE CODE section.
> Do not skip the onboarding questions — the answers shape the entire system.

---

## 📌 Project Summary

**NURA** is a fully local, omnichannel AI customer service backend that:
- Runs 100% on a company server using **Ollama** (no cloud AI dependency)
- Exposes a **single REST API** that any platform can connect to
- Follows company guidelines via a **RAG pipeline** (reads your handbook)
- Supports **multiple channels** (WhatsApp, Telegram, Web, Email, etc.) through a unified adapter layer
- Escalates to **human agents** when needed
- Logs everything to **PostgreSQL** for analytics

**Stack:** Python (FastAPI) · Ollama · LlamaIndex · ChromaDB · Redis · PostgreSQL · Docker Compose

---

## 🧠 INSTRUCTIONS FOR CLAUDE CODE

> You are building NURA from scratch. Follow these steps **in order**.
> At each phase, complete all tasks before moving to the next.
> When you need information from the user, **ask clearly and wait for the answer**.

---

## 🔧 STEP 0 — Install Required Skills from Anthropic Skills Repo

Before writing any code, run these commands to install the skills needed for this project:

```bash
# Register the Anthropic skills marketplace
/plugin marketplace add anthropics/skills

# Install the example skills (contains FastAPI, Docker, and backend patterns)
/plugin install example-skills@anthropic-agent-skills

# Install document skills (needed for handbook PDF ingestion features)
/plugin install document-skills@anthropic-agent-skills
```

After installing, confirm skills are active before proceeding.

---

## 📋 STEP 1 — Onboarding: Ask the User These Questions

**Before writing a single line of code**, ask the user the following questions one section at a time. Store the answers — they will be used throughout the build.

### Section A: Company Identity
Ask:
```
1. What is your company name?
2. What is your company's primary language? (e.g., English, Arabic, Kurdish, or multilingual)
3. What industry are you in? (e.g., telecom, retail, healthcare, real estate, tech)
4. What should the AI agent be named? (default: NURA)
5. What tone should NURA use? (formal / friendly / neutral)
```

### Section B: Server & Infrastructure
Ask:
```
6. What is your server OS? (Ubuntu 22.04 recommended)
7. How much RAM does the server have? (this affects model selection)
   - Under 8GB → will use phi3:mini
   - 8–16GB  → will use mistral:7b
   - 16GB+   → will use llama3.1:8b (recommended)
8. What is the server's local IP or hostname where NURA will run?
9. Do you already have Docker and Docker Compose installed? (yes/no)
10. Do you already have Ollama installed? (yes/no)
```

### Section C: Channels
Ask:
```
11. Which channels do you want to connect? (select all that apply)
    [ ] Website chat widget
    [ ] WhatsApp Business API
    [ ] Telegram Bot
    [ ] Facebook Messenger
    [ ] Email (IMAP/SMTP)
    [ ] Microsoft Teams
    [ ] Mobile App (iOS/Android REST)
    [ ] Internal staff portal only

12. For WhatsApp (if selected): Do you have a Meta Business Account and WhatsApp Business API access?
13. For Telegram (if selected): Do you have a Telegram Bot Token?
14. For Email (if selected): What is your support email address and SMTP provider?
```

### Section D: Knowledge Base
Ask:
```
15. Do you have your company handbook/guidelines ready as a file? (PDF, DOCX, or TXT)
    If yes: please provide the file path or upload it now.
    If no: I will create a sample handbook template you can fill in.

16. What topics does your handbook cover? (e.g., refund policy, shipping, account management, complaints)
    List the main sections so I can validate the RAG chunking strategy.

17. What should NURA do when it doesn't know the answer?
    a) Say "I don't have that information, let me connect you with a team member"
    b) Try its best and flag it as uncertain
    c) Always escalate to human immediately
```

### Section E: Human Handoff
Ask:
```
18. Do you want a human agent handoff system? (yes/no)
19. If yes: How many human agents will use the system simultaneously?
20. What triggers should cause escalation to a human?
    [ ] Customer explicitly asks for a human
    [ ] Two failed answer attempts
    [ ] Detected angry/negative sentiment
    [ ] Specific keywords (e.g., "legal", "lawsuit", "manager")
    [ ] High-value transaction above a threshold
```

### Section F: Admin Panel
Ask:
```
21. Do you want an Admin Panel web interface? (yes/no)
22. If yes: What language should the Admin Panel UI be in?
23. Who will manage the system? (IT team, customer care team, or both)
```

---

## 🏗️ STEP 2 — Scaffold the Project Structure

After collecting all answers, create this folder structure:

```
nura/
├── docker-compose.yml
├── .env                          ← generated from user answers
├── .env.example
├── README.md                     ← auto-generated setup guide
│
├── api/                          ← FastAPI backend (the core)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                   ← app entry point
│   ├── config.py                 ← loads from .env
│   ├── routes/
│   │   ├── message.py            ← POST /v1/message
│   │   ├── session.py            ← session management routes
│   │   ├── handoff.py            ← human escalation routes
│   │   ├── knowledge.py          ← knowledge base management
│   │   └── health.py             ← GET /v1/health
│   ├── core/
│   │   ├── orchestrator.py       ← routes messages through RAG → LLM
│   │   ├── rag_engine.py         ← LlamaIndex RAG pipeline
│   │   ├── session_manager.py    ← Redis-backed conversation memory
│   │   ├── handoff_controller.py ← escalation logic
│   │   ├── sentiment.py          ← basic sentiment detection
│   │   └── logger.py             ← structured logging to PostgreSQL
│   ├── adapters/                 ← one file per channel
│   │   ├── base.py               ← abstract adapter class
│   │   ├── web_widget.py
│   │   ├── whatsapp.py
│   │   ├── telegram.py
│   │   ├── messenger.py
│   │   ├── email_adapter.py
│   │   └── teams.py
│   ├── models/
│   │   ├── message.py            ← Pydantic models
│   │   ├── session.py
│   │   └── response.py
│   └── db/
│       ├── postgres.py           ← DB connection + queries
│       └── migrations/           ← SQL migration files
│
├── ingestion/                    ← handbook processing scripts
│   ├── ingest.py                 ← main ingestion script
│   ├── chunker.py                ← text splitting logic
│   └── handbook/                 ← place handbook files here
│       └── .gitkeep
│
├── admin/                        ← React admin panel
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── pages/
│       │   ├── Dashboard.jsx     ← analytics overview
│       │   ├── LiveQueue.jsx     ← active conversations
│       │   ├── SessionViewer.jsx ← past conversations
│       │   └── KnowledgeBase.jsx ← upload/manage handbook
│       └── components/
│
└── scripts/
    ├── setup.sh                  ← first-time setup script
    ├── pull_models.sh            ← pulls correct Ollama model based on RAM
    └── backup.sh                 ← PostgreSQL + ChromaDB backup
```

---

## ⚙️ STEP 3 — Generate the .env File

Using the answers from Step 1, auto-generate the `.env` file:

```env
# NURA Configuration — Auto-generated by Claude Code
# Generated: {DATE}

# === COMPANY ===
COMPANY_NAME="{answer_1}"
AGENT_NAME="{answer_4}"
AGENT_TONE="{answer_5}"          # formal | friendly | neutral
PRIMARY_LANGUAGE="{answer_2}"

# === SERVER ===
API_HOST=0.0.0.0
API_PORT=8000
OLLAMA_HOST=http://ollama:11434

# === MODEL SELECTION (based on RAM) ===
# < 8GB  → phi3:mini
# 8-16GB → mistral:7b
# 16GB+  → llama3.1:8b
LLM_MODEL="{auto_selected_from_answer_7}"
EMBEDDING_MODEL=nomic-embed-text

# === DATABASE ===
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=nura_db
POSTGRES_USER=nura_user
POSTGRES_PASSWORD={auto_generated_secure_password}

# === REDIS ===
REDIS_HOST=redis
REDIS_PORT=6379

# === CHROMADB ===
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# === RAG SETTINGS ===
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=64
RAG_TOP_K=3
UNKNOWN_ANSWER_BEHAVIOR="{answer_17}"   # escalate | uncertain | handoff

# === HANDOFF ===
HANDOFF_ENABLED={answer_18}
HANDOFF_TRIGGERS=angry_sentiment,explicit_request,two_failures

# === ACTIVE CHANNELS (set to true/false based on answer_11) ===
CHANNEL_WEB_WIDGET={true/false}
CHANNEL_WHATSAPP={true/false}
CHANNEL_TELEGRAM={true/false}
CHANNEL_MESSENGER={true/false}
CHANNEL_EMAIL={true/false}
CHANNEL_TEAMS={true/false}

# === CHANNEL CREDENTIALS (fill in after setup) ===
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
TELEGRAM_BOT_TOKEN=
MESSENGER_PAGE_TOKEN=
MESSENGER_VERIFY_TOKEN=
EMAIL_IMAP_HOST=
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=
EMAIL_SMTP_PORT=587
EMAIL_ADDRESS={answer_14}
EMAIL_PASSWORD=

# === ADMIN PANEL ===
ADMIN_ENABLED={answer_21}
ADMIN_PORT=3000
ADMIN_SECRET_KEY={auto_generated}
```

---

## 🐳 STEP 4 — Build docker-compose.yml

Generate a complete Docker Compose file with these services:

```yaml
# Required services:
services:
  nura-api:        # FastAPI — port 8000
  ollama:          # Ollama LLM server — port 11434
  chromadb:        # Vector database — port 8001
  postgres:        # Conversation logs — port 5432
  redis:           # Session cache — port 6379
  nura-admin:      # React admin panel — port 3000 (if answer_21 = yes)

# All services on a shared internal Docker network: nura_network
# Only nura-api and nura-admin exposed to host network
# Ollama must have GPU passthrough if available (--gpus all)
# Postgres data persisted to named volume: nura_postgres_data
# ChromaDB data persisted to: nura_chroma_data
# Ollama models persisted to: nura_ollama_models
```

---

## 🧠 STEP 5 — Build the Core API

### 5.1 The Universal Message Endpoint
Build `POST /v1/message` — this is NURA's heart:

```
Input (channel-agnostic):
{
  "session_id": "string",        ← unique per conversation
  "channel": "web|whatsapp|telegram|email|messenger|teams",
  "customer_id": "string",       ← unique per customer
  "message": "string",           ← the customer's text
  "metadata": {}                 ← optional channel-specific data
}

Processing flow:
1. Validate request (auth token in header)
2. Load or create session from Redis
3. Run sentiment check on message
4. Check if handoff trigger is met → if yes, route to handoff controller
5. Run RAG engine → retrieve top-K handbook chunks
6. Build prompt: system_prompt + handbook_context + conversation_history + message
7. Send to Ollama → get response
8. Save to session (Redis) and log to PostgreSQL
9. Return response

Output:
{
  "session_id": "string",
  "response": "string",          ← NURA's reply
  "channel": "string",
  "escalated": false,            ← true if handed off to human
  "agent_id": null,              ← human agent ID if escalated
  "confidence": 0.87             ← how confident RAG was (0-1)
}
```

### 5.2 System Prompt Template
Generate this dynamically using .env values:

```
You are {AGENT_NAME}, a {AGENT_TONE} customer care agent for {COMPANY_NAME}.

LANGUAGE: Always respond in {PRIMARY_LANGUAGE}. 
If the customer writes in a different language, match their language.

YOUR ROLE:
- Help customers with their questions and requests
- Always follow the guidelines provided in the HANDBOOK CONTEXT below
- Be concise, clear, and helpful
- Never make up information that is not in the handbook

HANDBOOK CONTEXT (use this to answer):
---
{rag_retrieved_chunks}
---

CONVERSATION SO FAR:
{conversation_history}

RULES:
1. If the answer is not in the handbook context, say: 
   "I don't have specific information on that. Let me connect you with a team member."
2. Never discuss competitors
3. Never promise things not in the handbook
4. If a customer is upset, acknowledge their frustration before answering
5. Keep responses under 3 sentences unless a detailed explanation is needed
```

### 5.3 Other Endpoints to Build

```
POST   /v1/session/start         → creates new session, returns session_id
GET    /v1/session/{id}          → returns full conversation history
DELETE /v1/session/{id}          → closes and archives session
POST   /v1/handoff/{id}          → escalates session to human queue
POST   /v1/handoff/{id}/resolve  → human marks session as resolved
GET    /v1/queue                  → lists all sessions pending human handoff
POST   /v1/knowledge/ingest      → triggers handbook re-ingestion
GET    /v1/analytics/summary     → returns stats for admin dashboard
GET    /v1/health                → returns system health status
```

---

## 📚 STEP 6 — Build the RAG Engine

Using **LlamaIndex** with local Ollama embeddings:

```python
# Key configuration:
# - Embedding: OllamaEmbedding(model_name="nomic-embed-text")
# - Vector store: ChromaVectorStore
# - LLM: Ollama(model=LLM_MODEL, base_url=OLLAMA_HOST)
# - Chunk size: RAG_CHUNK_SIZE (from .env)
# - Top-K retrieval: RAG_TOP_K (from .env)

# Ingestion pipeline (ingestion/ingest.py):
# 1. Read all files from ingestion/handbook/
# 2. Support: PDF, DOCX, TXT, MD
# 3. Split into chunks with overlap
# 4. Embed each chunk using nomic-embed-text via Ollama
# 5. Store in ChromaDB collection: "nura_handbook"
# 6. Print confirmation of how many chunks were stored

# Query pipeline (called per message):
# 1. Embed customer message
# 2. Search ChromaDB for top-K similar chunks
# 3. Return chunks + similarity scores
# 4. Inject into system prompt
```

---

## 📡 STEP 7 — Build Channel Adapters

Build only the adapters for channels selected in answer_11.

Each adapter must implement this interface:
```python
class BaseAdapter:
    def parse_incoming(self, raw_payload: dict) -> StandardMessage
    def format_outgoing(self, response: NURAResponse) -> dict
    def verify_webhook(self, request) -> bool
```

### Web Widget Adapter
- Accepts direct REST calls from the frontend widget
- No webhook verification needed
- Returns JSON directly

### WhatsApp Adapter
- Receives Meta webhook payload
- Verifies with `WHATSAPP_TOKEN`
- Extracts message text from `entry[0].changes[0].value.messages[0].text.body`
- Sends reply via Meta Graph API: `POST /messages`

### Telegram Adapter
- Receives Telegram webhook: `{"message": {"text": "...", "chat": {"id": "..."}}}`
- Sends reply via `https://api.telegram.org/bot{TOKEN}/sendMessage`

### Email Adapter
- Polls IMAP inbox every 60 seconds
- Parses subject + body as the customer message
- Uses session_id = email thread ID
- Replies via SMTP

---

## 👤 STEP 8 — Human Handoff System (if answer_18 = yes)

```
Handoff flow:
1. Trigger detected (from answer_20 selections)
2. NURA sends handoff message to customer: 
   "I'm connecting you with one of our team members. Please hold."
3. Session status changes to: "PENDING_HANDOFF" in Redis
4. Session appears in Admin Panel live queue
5. Human agent clicks "Accept" → status: "HUMAN_ACTIVE"
6. All further messages from customer go directly to human agent
7. Human replies through Admin Panel → NURA delivers to customer's channel
8. Human clicks "Resolve" → session archived, status: "RESOLVED"

Sentiment detection (basic):
- Maintain a negative_score counter per session
- Keywords that increase score: angry, frustrated, terrible, refund, lawsuit, 
  useless, horrible, cancel, manager, supervisor, unacceptable
- If score >= 2 in one session → trigger handoff
```

---

## 🖥️ STEP 9 — Admin Panel (if answer_21 = yes)

Build a React app with these pages:

### Dashboard (/)
- Total conversations today / this week / this month
- Resolution rate (resolved without handoff / total)
- Average response time
- Top 10 questions asked (word frequency from logs)
- Active sessions right now
- Channel breakdown (pie chart)

### Live Queue (/queue)
- Table of all sessions in PENDING_HANDOFF status
- Columns: Session ID, Channel, Customer ID, Wait Time, First Message Preview
- "Accept" button per row
- Real-time updates via WebSocket or polling every 5 seconds

### Session Viewer (/sessions)
- Search by customer_id, date, channel, or keyword
- Full conversation history view per session
- Show: timestamps, channel, escalation status, RAG confidence scores

### Knowledge Base (/knowledge)
- Upload new handbook files (PDF, DOCX, TXT)
- List currently ingested documents
- "Re-ingest All" button
- Ingestion log (last run time, chunks stored)

### Settings (/settings)
- Edit AGENT_NAME, AGENT_TONE, system prompt
- Switch Ollama model (dropdown of available pulled models)
- Toggle channels on/off
- Change handoff triggers

---

## 📜 STEP 10 — Generate Setup Scripts

### scripts/setup.sh
```bash
# This script runs on first deployment:
# 1. Check Docker is installed
# 2. Check docker compose is installed
# 3. Run: docker compose up -d
# 4. Wait for Ollama to be healthy
# 5. Run: ollama pull {LLM_MODEL}
# 6. Run: ollama pull nomic-embed-text
# 7. Run database migrations
# 8. Print: "NURA is ready! API running on http://{SERVER_IP}:8000"
# 9. Print: "Admin Panel: http://{SERVER_IP}:3000" (if enabled)
# 10. Print: "Run handbook ingestion: docker exec nura-api python ingestion/ingest.py"
```

### scripts/pull_models.sh
```bash
# Pulls the right model based on available RAM:
RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$RAM" -lt 8 ]; then
  ollama pull phi3:mini
elif [ "$RAM" -lt 16 ]; then
  ollama pull mistral:7b
else
  ollama pull llama3.1:8b
fi
ollama pull nomic-embed-text
```

---

## 📄 STEP 11 — Auto-Generate README.md

Generate a README for the project that includes:
1. What NURA is (one paragraph)
2. Architecture diagram (ASCII)
3. Prerequisites (Docker, 8GB+ RAM, Linux)
4. Quick start: `git clone → cp .env.example .env → ./scripts/setup.sh`
5. How to ingest the handbook
6. API reference for `/v1/message`
7. How to connect each channel (with links to Meta, Telegram docs)
8. How to add a new channel adapter
9. Backup and restore instructions

---

## ✅ STEP 12 — Validation Checklist

Before telling the user NURA is ready, verify:

```
[ ] docker compose up starts all services without errors
[ ] GET /v1/health returns 200 with all services green
[ ] POST /v1/message with a test message returns a coherent response
[ ] Ollama model is loaded and responding
[ ] ChromaDB has chunks stored (> 0) after ingestion
[ ] Redis stores session correctly across two messages
[ ] PostgreSQL logs the conversation
[ ] Admin Panel loads (if enabled)
[ ] At least one channel adapter responds to a test webhook
[ ] Handoff trigger works (send "I want to speak to a manager")
```

---

## 🔐 Security Notes for Claude Code

When building, always:
- Generate random secrets for `POSTGRES_PASSWORD` and `ADMIN_SECRET_KEY`
- Add API key auth to all `/v1/*` endpoints (Bearer token in header)
- Never expose Ollama port (11434) or ChromaDB port (8001) outside Docker network
- Add rate limiting: max 30 requests/minute per customer_id
- Sanitize all inputs before passing to LLM (strip HTML, limit to 2000 chars)
- Log security events (auth failures, rate limit hits) to separate postgres table

---

## 📦 Skills Needed from anthropics/skills

The following skills from `https://github.com/anthropics/skills` are relevant to this project.
Claude Code should install and use them:

| Skill | Why Needed |
|---|---|
| `document-skills` | For processing PDF/DOCX handbook files in the ingestion pipeline |
| `example-skills` | Contains FastAPI and backend patterns to follow |

Install commands:
```bash
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```

---

## 🗺️ Build Order Summary

```
Step 0  → Install skills from anthropics/skills repo
Step 1  → Ask user all onboarding questions (REQUIRED before any code)
Step 2  → Scaffold project folder structure
Step 3  → Generate .env from user answers
Step 4  → Generate docker-compose.yml
Step 5  → Build FastAPI core (/v1/message + other endpoints)
Step 6  → Build RAG engine (LlamaIndex + ChromaDB + Ollama)
Step 7  → Build channel adapters (only selected channels)
Step 8  → Build human handoff system (if selected)
Step 9  → Build Admin Panel React app (if selected)
Step 10 → Generate setup scripts
Step 11 → Generate README.md
Step 12 → Run validation checklist
```

**After Step 12 passes:** Tell the user:
> "NURA is ready. Run `./scripts/setup.sh` on your server to deploy.
> Place your handbook files in `ingestion/handbook/` then run the ingestion script.
> Your API is available at `http://{SERVER_IP}:8000/v1/message`."

---

*NURA Manifest v1.0 — Built for Claude Code*
*Project: Neural Unified Response Agent*
*Tagline: "One brain. Every channel."*
