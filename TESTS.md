# NURA Backend Test Suite Documentation

## Overview

The NURA backend test suite (`tests/test_backend_phase1.py`) provides comprehensive coverage of critical business logic flows using pytest. Tests use mock/fake implementations to avoid external dependencies and ensure deterministic, fast execution.

---

## Running Tests

### Run all tests
```bash
docker compose exec nura-api pytest -v
```

### Run specific test
```bash
docker compose exec nura-api pytest tests/test_backend_phase1.py::test_message_endpoint_generates_response_without_external_services -v
```

### Run with output
```bash
docker compose exec nura-api pytest -vv -s
```

---

## Test Categories & Details

### 1. Configuration & Validation Tests

#### `test_production_requires_ml_artifact_hashes`
**What it does:** Validates that production deployments require ML artifact hash verification.

**How it works:**
- Sets `APP_ENV=production` and `ML_REQUIRE_ARTIFACT_HASHES=false`
- Attempts to create a Settings object
- Expects a ValueError with "ML_REQUIRE_ARTIFACT_HASHES" in the message

**Why it matters:** Prevents accidentally deploying with unsigned ML models in production, protecting against model tampering.

---

#### `test_production_rejects_weak_admin_password`
**What it does:** Ensures production environment rejects weak admin passwords.

**How it works:**
- Sets `APP_ENV=production`
- Tries to create Settings with `ADMIN_PASSWORD=password` (weak password)
- Expects a ValueError with "ADMIN_PASSWORD" in the message

**Why it matters:** Production deployments must have strong passwords (≥12 characters, not common, not matching username).

---

### 2. Message Flow Tests

#### `test_message_endpoint_generates_response_without_external_services`
**What it does:** Tests that the message endpoint returns AI-generated responses correctly.

**How it works:**
1. Creates a mock session with customer message
2. Mocks `process_customer_message` to return:
   - Response text: "جواب تجريبي" (Arabic test response)
   - Confidence: 0.91
   - Source: "openai"
   - No escalation
3. Sends POST to `/v1/message` with customer message "مرحبا" (Arabic "hello")
4. Validates response contains session_id, response text, confidence, source

**Why it matters:** Verifies the core message processing pipeline works end-to-end without OpenAI/external APIs.

---

#### `test_message_endpoint_escalates_with_handoff_reason`
**What it does:** Tests that escalation to human agents includes proper handoff reason.

**How it works:**
1. Creates a session in `pending_handoff` status
2. Sets `handoff_reason=explicit_request` in metadata
3. Mocks `process_customer_message` to return escalated=true
4. Sends message requesting agent: "أريد التحدث مع موظف" (Arabic "I want to speak with an agent")
5. Validates:
   - Response has `escalated=true`
   - Session status is `pending_handoff`
   - Handoff reason is preserved

**Why it matters:** Ensures when customers ask for agents, the handoff is tracked with the right reason for analytics.

---

### 3. Handoff Management Tests

#### `test_direct_handoff_creates_pending_session`
**What it does:** Tests the direct human handoff flow (customer requests agent directly).

**How it works:**
1. Mocks `get_or_create_session`, `save_session`, `log_session_outcome`
2. POSTs to `/v1/handoff/direct` with:
   - session_id, customer_id, channel, reason="direct_request"
3. Validates:
   - Response has `ok=true` and `escalated=true`
   - Session status becomes `pending_handoff`
   - Handoff reason is logged
   - Session token is returned

**Why it matters:** Validates that customers can directly request agent conversations with proper tracking.

---

#### `test_accept_handoff_records_accept_timestamp`
**What it does:** Tests that when an agent accepts a pending handoff, accept time is recorded.

**How it works:**
1. Creates a session in `pending_handoff` status with reason="bad_feedback"
2. Mocks session retrieval and saving
3. POSTs to `/v1/handoff/s1/accept?agent_id=agent-a` with auth headers
4. Validates:
   - Session status changes to `human_active`
   - Agent is assigned: `assigned_agent=agent-a`
   - Timestamp recorded in `accepted_at`
   - Outcome logged with status="accepted" and original handoff reason

**Why it matters:** Time-to-accept is a critical SLA metric. This ensures accurate measurement.

---

### 4. Session Resolution Tests

#### `test_resolve_session_logs_detailed_outcome`
**What it does:** Tests that resolving a session captures full resolution details for analytics.

**How it works:**
1. Creates a session in `human_active` status
2. Sets `accepted_at` to 5 minutes ago and `handoff_reason=explicit_request`
3. POSTs to `/v1/session/s1/resolve` with:
   - status="solved"
   - issue_category="connectivity"
   - root_cause="apn_settings"
   - resolution_notes="Customer was guided through APN setup."
   - resolved_by="Agent"
4. Validates:
   - Response is ok
   - Session status becomes `resolved`
   - Outcome logged with all provided details
   - Time-to-resolution is calculated and ≥ 0

**Why it matters:** Complete resolution tracking enables reporting on issue types, root causes, and SLA metrics.

---

### 5. Session Access Control Tests

#### `test_customer_session_token_allows_message_access`
**What it does:** Tests that customers can view their sessions using a session token.

**How it works:**
1. Creates a session with `customer_token=customer-secret` in metadata
2. Tests two scenarios:
   - **Access with correct token:** GET `/v1/session/s1/messages` with `X-Session-Token: customer-secret`
     - Expects status 200 and returns session status
   - **Access with wrong token:** GET with `X-Session-Token: wrong`
     - Expects status 401 (Unauthorized)

**Why it matters:** Ensures customers can only view their own sessions and prevents cross-session data leaks.

---

### 6. Admin Authentication Tests

#### `test_admin_login_and_me`
**What it does:** Tests admin login flow and identity verification.

**How it works:**
1. Mocks `verify_db_password` to return valid admin user with role="admin"
2. Mocks `get_db_pool` to return user data for token validation
3. POSTs to `/v1/auth/login` with username and password
4. Extracts `access_token` from response
5. GETs `/v1/auth/me` with Bearer token
6. Validates response includes role="admin"

**Why it matters:** Verifies the JWT login flow works and tokens properly identify users.

---

#### `test_admin_token_fails_after_version_role_or_active_change`
**What it does:** Tests that admin tokens become invalid when user properties change (security feature).

**How it works:**
1. Creates a valid admin token for user with role="admin", token_version=0, is_active=true
2. Verifies token is initially valid
3. Increments `token_version` in DB → token becomes invalid
4. Resets version, changes `role` to "viewer" → token becomes invalid
5. Resets role, sets `is_active=false` → token becomes invalid

**Why it matters:** Ensures that deactivating a user, changing their role, or revoking sessions invalidates existing tokens immediately. This is critical for security when an admin is compromised.

---

#### `test_user_role_active_and_password_changes_bump_token_version`
**What it does:** Tests that role/active/password changes increment token_version to revoke sessions.

**How it works:**
1. Creates admin user in fake DB pool
2. Mocks hash_password to simple prefix
3. Makes three requests as admin:
   - PATCH `/v1/users/agent1` with new role
   - PATCH `/v1/users/agent1` with is_active=false
   - POST `/v1/users/agent1/password` with new password
4. Verifies that all 3 operations run UPDATE with `token_version = token_version + 1`

**Why it matters:** Ensures that any user property change invalidates existing sessions, preventing compromised tokens from persisting.

---

### 7. Cases & Suggestions Tests

#### `test_public_suggestion_endpoint_creates_case`
**What it does:** Tests that public suggestion endpoint creates support cases.

**How it works:**
1. Mocks `create_suggestion_case` and `get_session`
2. POSTs to `/v1/suggestions` with:
   - message: "اقتراح لتحسين سرعة الرد داخل التطبيق" (Arabic suggestion)
   - customer_id: "cust-suggest"
   - channel: "web"
3. Validates response includes case_number and passed data matches

**Why it matters:** Allows customers to submit suggestions from the widget, creating trackable back-office cases.

---

#### `test_create_suggestion_case_uses_suggestions_department`
**What it does:** Tests that suggestion cases are routed to the suggestions department.

**How it works:**
1. Creates fake DB pool for suggestion creation
2. Calls `create_suggestion_case()` async function with:
   - message in Arabic
   - customer_id, channel, actor, origin
3. Validates:
   - Case number incremented properly (ends with "-00002")
   - Department is "suggestions"
   - Channel is "telegram"
   - Source is "suggestion"
   - Tags include "telegram"

**Why it matters:** Ensures suggestions are properly categorized and routed to the right team.

---

#### `test_telegram_pending_suggestion_creates_case`
**What it does:** Tests Telegram workflow for creating suggestion cases.

**How it works:**
1. Creates a Telegram session
2. Stores pending suggestion data in Redis: `{"tg:suggestion:123": session_id}`
3. Mocks `create_suggestion_case`, `append_turn`, and `_send` (Telegram message)
4. Calls `_handle_message()` with Telegram message about a suggestion
5. Validates:
   - Case created with correct channel/customer
   - Turn appended to conversation
   - Pending suggestion removed from Redis
   - Case number sent back to Telegram chat

**Why it matters:** Ensures Telegram users can make suggestions and receive confirmation in chat.

---

### 8. Session Durability Tests

#### `test_save_session_persists_durable_copy`
**What it does:** Tests that sessions are saved to both Redis (fast) and PostgreSQL (durable).

**How it works:**
1. Creates a session with session_id="durable-save"
2. Mocks Redis and PostgreSQL pools
3. Calls `save_session(session)`
4. Validates:
   - Session stored in Redis with key `session:durable-save`
   - Session also inserted into PostgreSQL with correct status

**Why it matters:** If Redis crashes, sessions are still retrievable from PostgreSQL, ensuring durability.

---

#### `test_get_session_restores_from_postgres_on_redis_miss`
**What it does:** Tests session recovery from PostgreSQL when Redis doesn't have it.

**How it works:**
1. Creates empty Redis (cache miss)
2. Creates PostgreSQL pool with a stored session in "durable-load" state:
   - status: `pending_handoff`
   - handoff_reason: "explicit_request"
   - history: one customer message
3. Calls `get_session("durable-load")`
4. Validates:
   - Session retrieved from PostgreSQL
   - Status and metadata restored correctly
   - Session re-cached in Redis for next access

**Why it matters:** Ensures sessions survive Redis restarts and can be restored transparently.

---

### 9. Background Job Queue Tests

#### `test_enqueue_job_pushes_json_to_redis`
**What it does:** Tests that jobs are properly queued for background processing.

**How it works:**
1. Mocks Redis
2. Calls `enqueue_job(JOB_INTENT_CLASSIFICATION, session_id="s1")`
3. Validates:
   - Job ID is returned
   - Job pushed to Redis queue list
   - Job JSON contains correct type and payload

**Why it matters:** Background jobs (like intent classification) must be reliable. This validates queueing.

---

#### `test_recover_stale_jobs_requeues_abandoned_processing_job`
**What it does:** Tests that abandoned jobs (processing >60 seconds) are re-queued.

**How it works:**
1. Creates a job in PROCESSING state with timestamp 20 minutes ago
2. Calls `recover_stale_jobs(stale_after_seconds=60)`
3. Validates:
   - Job removed from processing list
   - Job pushed back to queue
   - Attempt counter incremented

**Why it matters:** If a worker crashes mid-job, stale jobs must be recovered to prevent data loss.

---

#### `test_recover_stale_jobs_timestamps_unmarked_processing_job`
**What it does:** Tests that jobs without processing timestamp get timestamped (marked for monitoring).

**How it works:**
1. Creates a job in PROCESSING state with NO timestamp (edge case)
2. Calls `recover_stale_jobs()` with stale_after=60 seconds
3. Validates:
   - Job stays in processing list (not recovered yet)
   - `processing_started_at` field added with current time
   - `processing_worker` marked as "unknown"

**Why it matters:** Ensures we can detect anomalies (jobs without timestamps) that might indicate bugs.

---

#### `test_process_job_dispatches_intent_classifier`
**What it does:** Tests that job processing correctly routes to handler.

**How it works:**
1. Mocks `classify_and_log_message`
2. Calls `process_job()` with a JOB_INTENT_CLASSIFICATION job containing:
   - session_id="s1", customer_id="c1", channel="web", message_text="hi"
3. Validates that `classify_and_log_message` was called with correct payload

**Why it matters:** Jobs must be dispatched to the right handler. This validates the dispatcher.

---

### 10. Analytics & Dashboard Tests

#### `test_dashboard_returns_expected_kpis`
**What it does:** Tests that the dashboard endpoint aggregates correct KPIs.

**How it works:**
1. Mocks database with FakeDashboardPool returning pre-set KPI values
2. Calls `get_dashboard(days=30)`
3. Validates all KPI sections:
   - **Total metrics:** total_sessions=3, total_messages=5
   - **Feedback:** feedback_bad=1
   - **Knowledge gaps:** knowledge_gaps=2
   - **LLM usage:** llm_total_tokens=1234
   - **Intents:** top_intents includes connectivity
   - **Time periods:** today and previous_period message counts
   - **Deltas:** percent change calculated correctly
   - **Queue:** pending_handoffs=2, oldest_wait_seconds=300.0
   - **Cases:** unassigned=1, breakdown by owner
   - **Suggestions:** unassigned=1
   - **Attention items:** critical severity items flagged

**Why it matters:** The dashboard is the operations command center. All KPIs must be accurate.

---

#### `test_dashboard_delta_handles_zero_previous_period`
**What it does:** Tests edge case where previous period has zero messages.

**How it works:**
1. Calls `_pct_delta(10, 0)` → previous period=0, current=10
   - Expects percent=100.0, absolute=10.0 (infinite growth)
2. Calls `_pct_delta(0, 0)` → both periods=0
   - Expects percent=0.0 (no change when both are zero)

**Why it matters:** Prevents division-by-zero errors and correctly interprets growth from zero baseline.

---

#### `test_reports_returns_expected_sections`
**What it does:** Tests the detailed reports endpoint with deep analytics.

**How it works:**
1. Mocks database with FakeReportsPool
2. Calls `get_reports(days=30, channel="web")`
3. Validates all report sections:
   - **Period:** days=30, channel_filter="web"
   - **Knowledge gaps:** message_text, intent, sub_intent, gap_reason
   - **Intents:** billing with count=2
   - **Handoffs:** explicit_request reason with count=1
   - **Costs:** tokens=100, model info
   - **Bad feedback:** session_id="s1", original messages

**Why it matters:** Detailed reports enable root cause analysis and product improvement.

---

## Test Utilities & Mocks

### Fake Database Pools
Tests use fake database connection pools to avoid real PostgreSQL:

- **FakeDashboardPool/Conn:** Returns pre-set dashboard KPI values
- **FakeReportsPool/Conn:** Returns detailed analytics data
- **FakeSuggestionPool/Conn:** Simulates suggestion case creation
- **FakeAdminAuthPool/Conn:** Simulates admin user lookups
- **FakeUserAdminPool/Conn:** Simulates user updates
- **FakeSessionPool/Conn:** Simulates session persistence

### Fake Redis
Simulates Redis operations:
```python
FakeRedis()
  .storage      # dict for key-value data
  .lists        # dict for list operations
  .lpush()      # push to list
  .brpoplpush() # blocking pop/push
  .lrange()     # range query
  .publish()    # pub/sub
```

### Fake Session Creator
```python
make_session(session_id="s1", customer_id="cust-1", channel="web", status=SessionStatus.active)
```
Creates a session object with current timestamp for testing.

---

## Test Fixtures

### `auth_headers` (conftest.py)
```python
{"Authorization": "Bearer test-api-key"}
```
Standard auth header for admin endpoints.

### `build_app` (conftest.py)
Factory fixture that creates a FastAPI app with:
- Routers included under `/v1` prefix
- Rate limiter configured
- API key verification bypassed (for tests)

Example usage:
```python
client = TestClient(build_app(message_route.router))
```

---

## Running Tests in CI/CD

Tests are designed to run in Docker:
```bash
docker compose exec nura-api pytest -q
```

Expected output:
```
tests/test_backend_phase1.py::test_production_requires_ml_artifact_hashes PASSED
tests/test_backend_phase1.py::test_production_rejects_weak_admin_password PASSED
tests/test_backend_phase1.py::test_message_endpoint_generates_response_without_external_services PASSED
... (28 tests total)
======================== 28 passed in 2.34s ========================
```

---

## Adding New Tests

1. Create test function starting with `test_`
2. Use `monkeypatch` fixture to mock dependencies
3. Use `build_app` fixture to create FastAPI test client
4. Use `TestClient` from fastapi.testclient for requests
5. Assert on response status, JSON body, and side effects

Example:
```python
def test_new_feature(monkeypatch, build_app):
    from routes import my_route
    
    # Mock dependencies
    monkeypatch.setattr(my_route, "get_session", lambda *_: _async_value(session))
    
    # Create test client
    client = TestClient(build_app(my_route.router))
    
    # Make request
    response = client.post("/v1/endpoint", json={"data": "value"})
    
    # Assert
    assert response.status_code == 200
    assert response.json()["ok"] is True
```

---

## Coverage

Current test suite covers:
- ✅ Configuration validation (production safety)
- ✅ Message processing and escalation
- ✅ Handoff workflows (direct, accept, resolve)
- ✅ Session access control
- ✅ Admin authentication and token revocation
- ✅ Cases and suggestions
- ✅ Session durability (Redis + PostgreSQL)
- ✅ Background job queue
- ✅ Analytics and KPI aggregation

Not yet covered:
- ⏳ File uploads
- ⏳ Telegram integration (partial)
- ⏳ Knowledge base ingestion
- ⏳ ML model predictions
- ⏳ Performance under load
