# Future Implementation Phases

This document tracks the backend hardening work needed to move NURA from a strong MVP/internal pilot into a more reliable production-ready system.

## Progress Snapshot

Completed:

- Phase 1: Safety Net
- Phase 2: Real Migrations
- Phase 3: Durable Sessions
- Phase 4: Background Jobs
- Phase 5: Telegram Architecture
- Phase 6: Auth Upgrade
- Phase 7: Analytics Performance
- Phase 8: Observability
- Phase 9: Configuration Cleanup
- Phase 10: Refactor For Maintainability

Remaining production polish:

- Move API deployments to `TELEGRAM_POLLER_ENABLED=false` and run the standalone Telegram service.
- Replace environment-based admin user with a full user-management UI/table flow.
- Populate daily aggregate tables with scheduled jobs when traffic grows.
- Add external metrics/error tooling such as Prometheus and Sentry.

## Current Backend Assessment

NURA currently has a useful and working backend: FastAPI routes, Redis plus PostgreSQL-backed sessions, PostgreSQL logging, Alembic migrations, Redis-backed background jobs, RAG/OpenAI integration, human handoff, analytics, reports, and early multi-channel support.

Several major reliability risks have now been reduced:

- Critical backend flows have automated tests.
- Redis sessions now have a PostgreSQL durable copy.
- Alembic exists as the migration path.
- Intent classification and escalation webhooks use a Redis-backed job queue.

The remaining important production concerns are operational:

- Dedicated production deployment settings must be chosen carefully.
- Telegram should run in one standalone process in production.
- Admin users need a real management UI if multiple operators will use it.
- Aggregates and external observability should be enabled when traffic grows.

---

## Phase 1: Safety Net

Add automated backend tests before doing larger refactors.

Status: completed initial test suite. Current coverage includes message flow, handoff, accept, resolve, dashboard, reports, session-token access, durable sessions, and job queue dispatch.

Tasks:

- Add `pytest` and `pytest-asyncio`.
- Add test setup for FastAPI routes.
- Add test database and Redis configuration for local Docker.
- Cover the critical flows first:
  - `POST /v1/message`
  - direct handoff
  - accept handoff
  - resolve session
  - analytics dashboard
  - reports endpoint
  - session-token access
- Add one local test command:

```bash
python -m pytest
```

Goal:

Make future changes safer and catch broken flows before they reach the running app.

---

## Phase 2: Real Migrations

Move schema management out of API startup.

Status: completed initial Alembic migration path. Current database is at migration `20260430_002`. `DB_AUTO_INIT` still defaults to enabled so existing local/dev startup behavior remains compatible until deployments explicitly move to migrations.

Tasks:

- Add Alembic.
- Convert the current PostgreSQL schema into migration `001_initial_schema`.
- Add migration coverage for:
  - `conversation_logs`
  - `tree_clicks`
  - `widget_events`
  - `chat_turns`
  - `security_logs`
  - `message_feedback`
  - `message_insights`
  - `session_outcomes`
  - `llm_usage_logs`
  - `ingestion_logs`
- Remove table mutation responsibility from `init_db`.
- Keep startup DB logic limited to connection checks.

Goal:

Make database changes predictable, reviewable, and safe across dev, staging, and production.

---

## Phase 3: Durable Sessions

Keep Redis fast, but make PostgreSQL the durable backup for sessions.

Status: implemented initial durable session storage. Redis remains the fast live cache, while PostgreSQL now stores a durable copy and is used to restore sessions on Redis misses.

Tasks:

- Add a `sessions` table in PostgreSQL.
- Store:
  - `session_id`
  - `customer_id`
  - `channel`
  - `status`
  - `history`
  - `metadata`
  - `created_at`
  - `updated_at`
- On every session save:
  - write to Redis
  - upsert to PostgreSQL
- On Redis miss:
  - load the session from PostgreSQL
  - restore it into Redis
- Configure a longer TTL for active human handoff sessions.

Goal:

Prevent active customer sessions from disappearing if Redis restarts or keys expire.

---

## Phase 4: Background Jobs

Replace important fire-and-forget tasks with durable jobs.

Status: completed initial Redis-backed job queue with retries. Intent classification and escalation webhooks now enqueue jobs. The API can run a local-compatible worker, and a standalone worker entrypoint/service is available for production split-out.

Tasks:

- Add a lightweight job queue.
- Preferred simple options:
  - ARQ with Redis
  - RQ with Redis
- Heavier option:
  - Celery
- Move these tasks into jobs:
  - intent classification
  - escalation webhook delivery
  - future report aggregation
  - Telegram outbound retry if needed
- Add retries and failure logs.
- Add a small worker Docker service.

Goal:

Make async side effects reliable instead of hoping raw `asyncio.create_task` finishes successfully.

---

## Phase 5: Telegram Architecture

Do not run Telegram polling inside the main API process in production.

Status: implemented a standalone Telegram worker entrypoint and optional Compose service. API polling remains available behind `TELEGRAM_POLLER_ENABLED` for local compatibility.

Tasks:

- Move Telegram long polling into a separate worker service, or switch to Telegram webhooks.
- Ensure only one Telegram consumer is active.
- Reuse the same customer message pipeline used by the web widget.
- Add logging for Telegram update IDs and delivery failures.
- Add retry/backoff for Telegram API failures.

Goal:

Prevent duplicate Telegram processing and keep the API process focused on HTTP traffic.

---

## Phase 6: Auth Upgrade

Move admin access from simple API-key use toward proper user auth.

Status: implemented admin login tokens, role-aware auth helpers, `/auth/login`, `/auth/me`, and login audit events. API-key compatibility remains for existing admin proxy/internal calls.

Tasks:

- Keep API key auth for internal service calls.
- Add admin login.
- Use secure session cookies or JWTs.
- Add roles:
  - `admin`
  - `agent`
  - `viewer`
- Protect admin endpoints by role.
- Add audit logs for:
  - login
  - failed login
  - accept handoff
  - resolve session
  - knowledge upload

Goal:

Make the admin panel safe for multiple real users and real operational use.

---

## Phase 7: Analytics Performance

Prepare reporting for larger datasets.

Status: implemented request date caps, added analytics indexes, and added daily aggregate tables for future scheduled aggregation.

Tasks:

- Add or verify indexes:
  - `conversation_logs(created_at, session_id)`
  - `conversation_logs(source, created_at)`
  - `session_outcomes(created_at, status)`
  - `message_insights(created_at, intent)`
  - `llm_usage_logs(created_at, operation)`
- Validate and cap `days` parameters.
- Recommended range:
  - minimum: `1`
  - maximum: `365`
- Add daily aggregate tables later:
  - `daily_message_stats`
  - `daily_cost_stats`
  - `daily_handoff_stats`
- Update dashboard queries to read from aggregates when data grows.

Goal:

Keep dashboard and reports fast as conversation volume increases.

---

## Phase 8: Observability

Make failures easier to see, debug, and measure.

Status: implemented request IDs, request/slow-request logging, in-memory request metrics, and protected `/v1/metrics`.

Tasks:

- Add structured JSON logs.
- Add request IDs.
- Log slow requests.
- Add error tracking, for example Sentry.
- Add basic metrics:
  - request count
  - request latency
  - OpenAI failures
  - Redis failures
  - PostgreSQL failures
  - handoff count
  - job failures
- Add dashboards or simple exported metrics later.

Goal:

Know when the system is failing before users tell you.

---

## Phase 9: Configuration Cleanup

Make environments explicit and safer.

Status: added `APP_ENV`, production-only secret validation, admin login config, Telegram worker flags, job config, and refreshed `.env.example`.

Tasks:

- Validate required environment variables on startup.
- Separate config expectations for:
  - development
  - staging
  - production
- Remove unsafe production defaults.
- Keep `.env.example` complete and secret-free.
- Cache external health checks so the dashboard does not repeatedly call OpenAI.
- Document each environment variable clearly.

Goal:

Make deployments repeatable and reduce surprises from missing or unsafe config.

---

## Phase 10: Refactor For Maintainability

Extract business logic out of route files.

Status: implemented shared `process_customer_message(...)` pipeline and moved web/Telegram message handling onto that path.

Tasks:

- Create one shared message pipeline:

```text
process_customer_message(session_id, customer_id, channel, message)
```

- Use the same pipeline for:
  - web widget
  - Telegram
  - future WhatsApp / Meta
  - future mobile app API
- Keep route files thin.
- Move analytics SQL into a reporting service.
- Move handoff state changes into a handoff service.
- Suggested service modules:
  - `MessageService`
  - `SessionService`
  - `HandoffService`
  - `ReportingService`
  - `ChannelService`

Goal:

Make new channels and future changes easier without duplicating the same logic in every route.

---

## Recommended Implementation Order

1. Safety net tests.
2. Durable sessions.
3. Background jobs.
4. Real migrations.
5. Shared message pipeline refactor.
6. Telegram worker or webhook cleanup.
7. Auth upgrade.
8. Analytics performance.
9. Observability.
10. Production configuration cleanup.

The first three phases should give the biggest reliability improvement. After those are done, the backend will be much closer to a real production service instead of a feature-rich MVP.
