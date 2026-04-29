from datetime import datetime, timedelta, timezone
import json

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
    logged = {}

    async def fake_get_or_create_session(session_id, customer_id, channel):
        return session

    async def fake_generate_response(session, message):
        return "جواب تجريبي", 0.91, "openai", "handbook.pdf"

    async def fake_append_turn(session, role, message, confidence=0.0, source="bot"):
        session.history.append(type("Turn", (), {"role": role, "message": message})())

    async def fake_log_conversation(**kwargs):
        logged.update(kwargs)

    async def fake_enqueue_job(job_type, **kwargs):
        logged["job_type"] = job_type
        logged["job_payload"] = kwargs

    monkeypatch.setattr(message_route, "get_or_create_session", fake_get_or_create_session)
    monkeypatch.setattr(message_route, "generate_response", fake_generate_response)
    monkeypatch.setattr(message_route, "check_handoff_triggers", lambda *_: (False, ""))
    monkeypatch.setattr(message_route, "append_turn", fake_append_turn)
    monkeypatch.setattr(message_route, "save_session", lambda session: _async_none())
    monkeypatch.setattr(message_route, "log_conversation", fake_log_conversation)
    monkeypatch.setattr(message_route, "enqueue_job", fake_enqueue_job)

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
    assert logged["customer_message"] == "مرحبا"
    assert logged["source"] == "openai"
    assert logged["job_type"] == message_route.JOB_INTENT_CLASSIFICATION
    assert logged["job_payload"]["message_text"] == "مرحبا"


def test_message_endpoint_escalates_with_handoff_reason(monkeypatch, build_app):
    from routes import message as message_route

    session = make_session()
    outcomes = []
    jobs = []

    async def fake_generate_response(session, message):
        return "model answer should be replaced", 0.88, "openai", None

    async def fake_log_session_outcome(**kwargs):
        outcomes.append(kwargs)

    async def fake_enqueue_job(job_type, **kwargs):
        jobs.append({"type": job_type, "payload": kwargs})

    monkeypatch.setattr(message_route, "get_or_create_session", lambda **_: _async_value(session))
    monkeypatch.setattr(message_route, "generate_response", fake_generate_response)
    monkeypatch.setattr(message_route, "check_handoff_triggers", lambda *_: (True, "explicit_request"))
    monkeypatch.setattr(message_route, "append_turn", lambda *_, **__: _async_none())
    monkeypatch.setattr(message_route, "save_session", lambda *_: _async_none())
    monkeypatch.setattr(message_route, "log_conversation", lambda **_: _async_none())
    monkeypatch.setattr(message_route, "log_session_outcome", fake_log_session_outcome)
    monkeypatch.setattr(message_route, "enqueue_job", fake_enqueue_job)

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
    assert outcomes[0]["status"] == "pending_handoff"
    assert outcomes[0]["handoff_reason"] == "explicit_request"
    assert [job["type"] for job in jobs] == [
        message_route.JOB_ESCALATION_WEBHOOK,
        message_route.JOB_INTENT_CLASSIFICATION,
    ]


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
