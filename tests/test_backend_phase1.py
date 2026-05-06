from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from models.session import Session, SessionStatus


def make_session(session_id="s1", customer_id="cust-1", channel="web", status=SessionStatus.active):
    now = datetime.now(timezone.utc).isoformat()
    return Session(
        session_id=session_id,
        customer_id=customer_id,
        channel=channel,
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_message_endpoint_generates_response_without_external_services(monkeypatch, build_app):
    from routes import message as message_route

    session = make_session()

    async def fake_process_customer_message(**kwargs):
        return SimpleNamespace(
            session=session,
            session_token="token",
            response_text="جواب تجريبي",
            confidence=0.91,
            source="openai",
            source_doc="handbook.pdf",
            escalated=False,
        )

    monkeypatch.setattr(message_route, "process_customer_message", fake_process_customer_message)

    client = TestClient(build_app(message_route.router))
    response = client.post(
        "/v1/message",
        json={"customer_id": "cust-1", "channel": "web", "message": "مرحبا"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "s1"
    assert body["response"] == "جواب تجريبي"
    assert body["escalated"] is False
    assert body["source"] == "openai"
    assert body["source_doc"] == "handbook.pdf"


def test_message_endpoint_escalates_with_handoff_reason(monkeypatch, build_app):
    from routes import message as message_route

    session = make_session()
    session.status = SessionStatus.pending_handoff
    session.metadata["handoff_reason"] = "explicit_request"

    async def fake_process_customer_message(**kwargs):
        return SimpleNamespace(
            session=session,
            session_token="token",
            response_text="handoff",
            confidence=0.88,
            source=None,
            source_doc=None,
            escalated=True,
        )

    monkeypatch.setattr(message_route, "process_customer_message", fake_process_customer_message)

    client = TestClient(build_app(message_route.router))
    response = client.post(
        "/v1/message",
        json={"customer_id": "cust-1", "channel": "web", "message": "أريد التحدث مع موظف"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert body["source"] is None
    assert session.status == SessionStatus.pending_handoff
    assert session.metadata["handoff_reason"] == "explicit_request"


def test_direct_handoff_creates_pending_session(monkeypatch, build_app):
    from routes import handoff as handoff_route

    session = make_session(session_id="direct-1")
    outcomes = []

    monkeypatch.setattr(handoff_route, "get_or_create_session", lambda **_: _async_value(session))
    monkeypatch.setattr(handoff_route, "save_session", lambda *_: _async_none())
    monkeypatch.setattr(handoff_route, "log_session_outcome", lambda **kwargs: _async_append(outcomes, kwargs))

    client = TestClient(build_app(handoff_route.router))
    response = client.post(
        "/v1/handoff/direct",
        json={"session_id": "direct-1", "customer_id": "cust-1", "channel": "web", "reason": "direct_request"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["escalated"] is True
    assert body["session_token"]
    assert session.status == SessionStatus.pending_handoff
    assert session.metadata["handoff_reason"] == "direct_request"
    assert outcomes[0]["handoff_reason"] == "direct_request"


def test_accept_handoff_records_accept_timestamp(monkeypatch, build_app, auth_headers):
    from routes import handoff as handoff_route

    session = make_session(status=SessionStatus.pending_handoff)
    session.metadata["handoff_reason"] = "bad_feedback"
    outcomes = []

    monkeypatch.setattr(handoff_route, "get_session", lambda *_: _async_value(session))
    monkeypatch.setattr(handoff_route, "save_session", lambda *_: _async_none())
    monkeypatch.setattr(handoff_route, "log_session_outcome", lambda **kwargs: _async_append(outcomes, kwargs))

    client = TestClient(build_app(handoff_route.router))
    response = client.post("/v1/handoff/s1/accept?agent_id=agent-a", headers=auth_headers)

    assert response.status_code == 200
    assert session.status == SessionStatus.human_active
    assert session.metadata["assigned_agent"] == "agent-a"
    assert session.metadata["accepted_at"]
    assert outcomes[0]["status"] == "accepted"
    assert outcomes[0]["handoff_reason"] == "bad_feedback"


def test_resolve_session_logs_detailed_outcome(monkeypatch, build_app, auth_headers):
    from routes import session as session_route

    session = make_session(status=SessionStatus.human_active)
    accepted_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    session.metadata["accepted_at"] = accepted_at.isoformat()
    session.metadata["handoff_reason"] = "explicit_request"
    outcomes = []

    monkeypatch.setattr(session_route, "get_session", lambda *_: _async_value(session))
    monkeypatch.setattr(session_route, "save_session", lambda *_: _async_none())
    monkeypatch.setattr(session_route, "publish_session_event", lambda *_: _async_none())
    monkeypatch.setattr(session_route, "log_session_outcome", lambda **kwargs: _async_append(outcomes, kwargs))

    client = TestClient(build_app(session_route.router))
    response = client.post(
        "/v1/session/s1/resolve",
        headers=auth_headers,
        json={
            "status": "solved",
            "issue_category": "connectivity",
            "root_cause": "apn_settings",
            "resolution_notes": "Fixed APN",
            "resolved_by": "agent-a",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert session.status == SessionStatus.resolved
    assert outcomes[0]["status"] == "solved"
    assert outcomes[0]["issue_category"] == "connectivity"
    assert outcomes[0]["handoff_reason"] == "explicit_request"
    assert outcomes[0]["time_to_resolution_seconds"] >= 0


def test_customer_session_token_allows_message_access(monkeypatch, build_app):
    from routes import session as session_route

    session = make_session()
    session.metadata["customer_token"] = "customer-secret"

    monkeypatch.setattr(session_route, "get_session", lambda *_: _async_value(session))

    client = TestClient(build_app(session_route.router))
    ok_response = client.get("/v1/session/s1/messages", headers={"X-Session-Token": "customer-secret"})
    denied_response = client.get("/v1/session/s1/messages", headers={"X-Session-Token": "wrong"})

    assert ok_response.status_code == 200
    assert ok_response.json()["status"] == SessionStatus.active.value
    assert denied_response.status_code == 401


def test_admin_login_and_me(monkeypatch, build_app):
    from routes import auth as auth_route
    from core import session_manager

    monkeypatch.setattr(
        auth_route,
        "verify_db_password",
        lambda username, password: _async_value({
            "username": username,
            "role": "admin",
            "display_name": "Admin",
            "is_active": True,
        }),
    )
    monkeypatch.setattr(session_manager, "get_redis", lambda: FakeAuthRedis())
    monkeypatch.setattr(auth_route, "log_security_event", lambda *_, **__: _async_none())
    client = TestClient(build_app(auth_route.router))
    login = client.post("/v1/auth/login", json={"username": "admin", "password": "password"})

    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_public_suggestion_endpoint_creates_case(monkeypatch, build_app):
    from routes import cases as cases_route

    created = {}

    async def fake_create_suggestion_case(**kwargs):
        created.update(kwargs)
        return {"case_number": "NURA-TEST-00001", "id": 10}

    monkeypatch.setattr(cases_route, "create_suggestion_case", fake_create_suggestion_case)
    monkeypatch.setattr(cases_route, "get_session", lambda *_: _async_value(None))

    client = TestClient(build_app(cases_route.router))
    response = client.post(
        "/v1/suggestions",
        json={
            "message": "اقتراح لتحسين سرعة الرد داخل التطبيق",
            "customer_id": "cust-suggest",
            "channel": "web",
        },
    )

    assert response.status_code == 200
    assert response.json()["case_number"] == "NURA-TEST-00001"
    assert created["message"] == "اقتراح لتحسين سرعة الرد داخل التطبيق"
    assert created["customer_id"] == "cust-suggest"
    assert created["channel"] == "web"


@pytest.mark.asyncio
async def test_create_suggestion_case_uses_suggestions_department(monkeypatch):
    from routes import cases as cases_route

    pool = FakeSuggestionPool()
    monkeypatch.setattr(cases_route, "get_db_pool", lambda: _async_value(pool))
    monkeypatch.setattr(cases_route, "is_valid_department_code", lambda code: code == "suggestions")

    result = await cases_route.create_suggestion_case(
        message="اقتراح تيليجرام مهم",
        customer_id="tg-1",
        channel="telegram",
        actor="telegram",
        origin="Telegram bot",
    )

    assert result["case_number"].endswith("-00002")
    assert pool.conn.insert_args["department"] == "suggestions"
    assert pool.conn.insert_args["channel"] == "telegram"
    assert pool.conn.insert_args["source"] == "suggestion"
    assert "telegram" in pool.conn.insert_args["tags"]


@pytest.mark.asyncio
async def test_telegram_pending_suggestion_creates_case(monkeypatch):
    from routes import telegram as telegram_route

    session = make_session(session_id="tg-session", customer_id="123", channel="telegram")
    redis = FakeTelegramRedis({"tg:suggestion:123": json.dumps({"session_id": "tg-session"})})
    sent = []
    created = {}
    appended = []

    async def fake_create_suggestion_case(**kwargs):
        created.update(kwargs)
        return {"case_number": "NURA-TEST-00003"}

    async def fake_append_turn(*args, **kwargs):
        appended.append((args, kwargs))

    monkeypatch.setattr(telegram_route, "get_redis", lambda: redis)
    monkeypatch.setattr(telegram_route, "_get_chat_session", lambda *_: _async_value(session))
    monkeypatch.setattr(telegram_route, "create_suggestion_case", fake_create_suggestion_case)
    monkeypatch.setattr(telegram_route, "append_turn", fake_append_turn)
    monkeypatch.setattr(telegram_route, "_send", lambda chat_id, text, **kwargs: _async_append(sent, {"chat_id": chat_id, "text": text, "kwargs": kwargs}))

    await telegram_route._handle_message({"chat": {"id": 123}, "text": "أقترح إضافة متابعة لحالة الطلب من داخل تيليجرام"})

    assert created["channel"] == "telegram"
    assert created["customer_id"] == "123"
    assert created["session_id"] == "tg-session"
    assert appended
    assert "tg:suggestion:123" in redis.deleted
    assert "NURA-TEST-00003" in sent[-1]["text"]


@pytest.mark.asyncio
async def test_save_session_persists_durable_copy(monkeypatch):
    from core import session_manager

    session = make_session(session_id="durable-save")
    redis = FakeRedis()
    pool = FakeSessionPool()

    monkeypatch.setattr(session_manager, "get_redis", lambda: redis)
    monkeypatch.setattr(session_manager, "get_db_pool", lambda: _async_value(pool))

    await session_manager.save_session(session)

    assert "session:durable-save" in redis.storage
    assert pool.conn.saved["session_id"] == "durable-save"
    assert pool.conn.saved["status"] == SessionStatus.active.value


@pytest.mark.asyncio
async def test_get_session_restores_from_postgres_on_redis_miss(monkeypatch):
    from core import session_manager

    now = datetime.now(timezone.utc)
    redis = FakeRedis()
    pool = FakeSessionPool(row={
        "session_id": "durable-load",
        "customer_id": "cust-1",
        "channel": "web",
        "status": SessionStatus.pending_handoff.value,
        "history": [{"role": "customer", "message": "hi", "timestamp": now.isoformat(), "source": "customer"}],
        "failure_count": 1,
        "negative_score": 2,
        "metadata": {"handoff_reason": "explicit_request"},
        "created_at": now,
        "updated_at": now,
    })

    monkeypatch.setattr(session_manager, "get_redis", lambda: redis)
    monkeypatch.setattr(session_manager, "get_db_pool", lambda: _async_value(pool))

    session = await session_manager.get_session("durable-load")

    assert session is not None
    assert session.session_id == "durable-load"
    assert session.status == SessionStatus.pending_handoff
    assert session.metadata["handoff_reason"] == "explicit_request"
    assert "session:durable-load" in redis.storage


@pytest.mark.asyncio
async def test_enqueue_job_pushes_json_to_redis(monkeypatch):
    from core import job_queue

    redis = FakeRedis()
    monkeypatch.setattr(job_queue, "get_redis", lambda: redis)

    job_id = await job_queue.enqueue_job(job_queue.JOB_INTENT_CLASSIFICATION, session_id="s1")

    assert job_id
    assert job_queue.JOB_QUEUE_KEY in redis.lists
    stored = json.loads(redis.lists[job_queue.JOB_QUEUE_KEY][0])
    assert stored["id"] == job_id
    assert stored["type"] == job_queue.JOB_INTENT_CLASSIFICATION
    assert stored["payload"]["session_id"] == "s1"


@pytest.mark.asyncio
async def test_process_job_dispatches_intent_classifier(monkeypatch):
    from core import intent_classifier, job_queue

    called = {}

    async def fake_classify_and_log_message(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(intent_classifier, "classify_and_log_message", fake_classify_and_log_message)

    await job_queue.process_job({
        "type": job_queue.JOB_INTENT_CLASSIFICATION,
        "payload": {"session_id": "s1", "customer_id": "c1", "channel": "web", "message_text": "hi"},
    })

    assert called["session_id"] == "s1"
    assert called["message_text"] == "hi"


@pytest.mark.asyncio
async def test_dashboard_returns_expected_kpis(monkeypatch):
    from routes import analytics

    monkeypatch.setattr(analytics, "get_db_pool", lambda: _async_value(FakeDashboardPool()))

    result = await analytics.get_dashboard(days=30, _=None)

    assert result["total_sessions"] == 3
    assert result["total_messages"] == 5
    assert result["feedback_bad"] == 1
    assert result["knowledge_gaps"] == 2
    assert result["llm_total_tokens"] == 1234
    assert result["top_intents"][0]["intent"] == "connectivity"
    assert result["today"]["messages"] == 5
    assert result["previous_period"]["messages"] == 5
    assert result["deltas"]["messages"]["percent"] == 0.0
    assert result["queue"]["pending_handoffs"] == 2
    assert result["queue"]["oldest_wait_seconds"] == 300.0
    assert result["cases"]["unassigned"] == 1
    assert result["cases"]["by_owner"][0]["owner"] == "Unassigned"
    assert result["suggestions"]["unassigned"] == 1
    assert result["attention_items"][0]["severity"] == "critical"


def test_dashboard_delta_handles_zero_previous_period():
    from routes.analytics import _pct_delta

    increased = _pct_delta(10, 0)
    flat = _pct_delta(0, 0)

    assert increased["percent"] == 100.0
    assert increased["absolute"] == 10.0
    assert flat["percent"] == 0.0


@pytest.mark.asyncio
async def test_reports_returns_expected_sections(monkeypatch):
    from routes import analytics

    monkeypatch.setattr(analytics, "get_db_pool", lambda: _async_value(FakeReportsPool()))

    result = await analytics.get_reports(days=30, channel="web", _=None)

    assert result["period_days"] == 30
    assert result["channel_filter"] == "web"
    assert len(result["knowledge_gaps"]) == 1
    assert result["intents"][0]["intent"] == "billing"
    assert result["handoffs"][0]["reason"] == "explicit_request"
    assert result["costs"][0]["total_tokens"] == 100
    assert result["bad_feedback"][0]["session_id"] == "s1"


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def acquire(self):
        return FakeAcquire(self.conn)


class FakeDashboardPool(FakePool):
    def __init__(self):
        self.conn = FakeDashboardConn()


class FakeDashboardConn:
    async def fetchrow(self, query, *args):
        if "COUNT(DISTINCT session_id) AS sessions" in query:
            return {"sessions": 3, "messages": 5, "escalations": 1}
        if "FROM conversation_logs" in query:
            return {"total_sessions": 3, "total_messages": 5, "avg_confidence": 0.8, "escalations": 1}
        if "FROM message_feedback" in query:
            return {"total": 3, "good": 2, "bad": 1}
        if "AVG(time_to_accept_seconds)" in query:
            return {"avg_accept": 30.0, "avg_resolution": 120.0, "resolved": 2}
        if "FROM message_insights" in query:
            return {"gaps": 2}
        if "FROM llm_usage_logs" in query:
            return {"cost": 0.001, "tokens": 1234}
        if "FROM sessions" in query:
            return {
                "pending_handoffs": 2,
                "human_active": 1,
                "oldest_wait_seconds": 300.0,
                "avg_wait_seconds": 90.0,
            }
        if "FROM support_cases" in query:
            return {
                "open_cases": 2,
                "escalated_cases": 1,
                "resolved_cases": 3,
                "cases_at_risk": 1,
                "cases_breached": 0,
                "cases_overdue": 0,
                "avg_case_resolution": 120.0,
                "new_suggestions": 1,
                "open": 2,
                "unassigned": 1,
                "breached": 1,
                "at_risk": 1,
                "new": 1,
            }
        return {}

    async def fetch(self, query, *args):
        now = datetime.now(timezone.utc)
        if "GROUP BY source" in query:
            return [{"source": "openai", "cnt": 2}]
        if "FROM tree_clicks" in query:
            return [{"topic_id": "internet", "topic_label": "Internet", "clicks": 4, "leaf_clicks": 2}]
        if "GROUP BY day" in query:
            return [{"day": now.date(), "messages": 5, "sessions": 3}]
        if "GROUP BY hour" in query:
            return [{"hour": 10, "messages": 5}]
        if "FROM widget_events" in query:
            return [{"event_type": "chat_open", "cnt": 3}]
        if "SELECT intent" in query:
            return [{"intent": "connectivity", "count": 2}]
        if "handoff_reason" in query:
            return [{"reason": "explicit_request", "count": 1}]
        if "COALESCE(owner" in query:
            return [{"owner": "Unassigned", "count": 1}, {"owner": "agent-a", "count": 1}]
        if "COALESCE(channel" in query:
            return [{"channel": "web", "count": 1}, {"channel": "telegram", "count": 1}]
        if "FROM support_cases" in query:
            return [{"department": "suggestions", "count": 2}]
        if "ORDER BY created_at DESC" in query:
            return [{
                "session_id": "s1",
                "channel": "web",
                "customer_message": "hello",
                "source": "openai",
                "confidence": 0.8,
                "escalated": False,
                "created_at": now,
            }]
        return []


class FakeReportsPool(FakePool):
    def __init__(self):
        self.conn = FakeReportsConn()


class FakeReportsConn:
    async def fetch(self, query, *args):
        now = datetime.now(timezone.utc)
        if "is_knowledge_gap = TRUE" in query:
            return [{
                "message_text": "missing",
                "intent": "billing",
                "sub_intent": "invoice",
                "gap_reason": "not_in_kb",
                "channel": "web",
                "created_at": now,
            }]
        if "GROUP BY intent, sub_intent" in query:
            return [{"intent": "billing", "sub_intent": "invoice", "count": 2}]
        if "handoff_reason" in query:
            return [{"reason": "explicit_request", "count": 1}]
        if "GROUP BY status" in query:
            return [{"status": "solved", "issue_category": "billing", "root_cause": "invoice", "count": 1, "avg_resolution": 15.0}]
        if "FROM llm_usage_logs" in query:
            return [{"model": "test-model", "operation": "chat", "prompt_tokens": 70, "completion_tokens": 30, "total_tokens": 100, "estimated_cost": 0.001}]
        if "FROM conversation_logs" in query and "GROUP BY channel" in query:
            return [{"channel": "web", "messages": 4}]
        if "FROM message_feedback" in query:
            return [{
                "session_id": "s1",
                "customer_message": "bad answer",
                "agent_response": "sorry",
                "source": "openai",
                "reason": "incorrect",
                "created_at": now,
            }]
        return []


class FakeSuggestionPool(FakePool):
    def __init__(self):
        self.conn = FakeSuggestionConn()


class FakeSuggestionConn:
    def __init__(self):
        self.insert_args = {}

    async def fetchval(self, query, *args):
        if "nextval" in query:
            return 2
        return 0

    async def fetchrow(self, query, *args):
        now = datetime.now(timezone.utc)
        self.insert_args = {
            "case_number": args[0],
            "session_id": args[1],
            "customer_id": args[2],
            "channel": args[3],
            "title": args[4],
            "description": args[5],
            "department": args[6],
            "tags": args[7],
            "internal_notes": args[8],
            "source": "suggestion",
            "created_by": args[11],
        }
        return {
            "id": 2,
            "case_number": args[0],
            "session_id": args[1],
            "customer_id": args[2],
            "channel": args[3],
            "title": args[4],
            "description": args[5],
            "department": args[6],
            "priority": "normal",
            "owner": None,
            "tags": args[7],
            "internal_notes": args[8],
            "source": "suggestion",
            "status": "open",
            "sla_status": "ok",
            "first_response_due_at": args[9],
            "sla_due_at": args[10],
            "sla_warned_at": None,
            "sla_breached_at": None,
            "resolved_at": None,
            "created_at": now,
            "updated_at": now,
            "created_by": args[11],
            "updated_by": args[11],
        }

    async def execute(self, query, *args):
        return "INSERT 0 1"


class FakeRedis:
    def __init__(self):
        self.storage = {}
        self.lists = {}

    async def get(self, key):
        return self.storage.get(key)

    async def setex(self, key, ttl, value):
        self.storage[key] = value
        return True

    async def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)
        return len(self.lists[key])

    async def brpoplpush(self, source, destination, timeout=0):
        values = self.lists.get(source) or []
        if not values:
            return None
        value = values.pop()
        self.lists.setdefault(destination, []).insert(0, value)
        return value

    async def lrem(self, key, count, value):
        values = self.lists.get(key) or []
        removed = 0
        kept = []
        for item in values:
            if item == value and (count == 0 or removed < abs(count)):
                removed += 1
                continue
            kept.append(item)
        self.lists[key] = kept
        return removed

    async def publish(self, channel, payload):
        return 1

    async def scan_iter(self, pattern):
        for key in list(self.storage):
            if key.startswith("session:"):
                yield key


class FakeTelegramRedis:
    def __init__(self, storage=None):
        self.storage = storage or {}
        self.deleted = []

    async def get(self, key):
        return self.storage.get(key)

    async def set(self, key, value, ex=None):
        self.storage[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.storage[key] = value
        return True

    async def delete(self, key):
        self.deleted.append(key)
        self.storage.pop(key, None)
        return 1


class FakeAuthRedis:
    async def exists(self, key):
        return 0


class FakeSessionPool(FakePool):
    def __init__(self, row=None):
        self.conn = FakeSessionConn(row=row)


class FakeSessionConn:
    def __init__(self, row=None):
        self.row = row
        self.saved = {}

    async def execute(self, query, *args):
        self.saved = {
            "session_id": args[0],
            "customer_id": args[1],
            "channel": args[2],
            "status": args[3],
            "history": json.loads(args[4]),
            "failure_count": args[5],
            "negative_score": args[6],
            "metadata": json.loads(args[7]),
            "created_at": args[8],
            "updated_at": args[9],
        }

    async def fetchrow(self, query, *args):
        return self.row

    async def fetch(self, query, *args):
        return []


async def _async_none(*args, **kwargs):
    return None


async def _async_value(value):
    return value


async def _async_append(items, value):
    items.append(value)
