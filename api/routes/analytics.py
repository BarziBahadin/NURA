import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import verify_api_key
from core.logger import log_message_feedback, log_tree_click, log_widget_event
from db.postgres import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

ALLOWED_EVENT_TYPES = {
    "chat_open", "chat_close", "lang_switch", "send_message",
    "tree_click", "tree_back", "tree_home", "followup_yes",
    "followup_no", "feedback_good", "feedback_bad", "direct_to_agent",
    "suggestion_open", "suggestion_submit",
}


ACTIVE_CASE_STATUSES = ("open", "pending", "in_progress", "waiting_customer", "escalated")


def _pct_delta(current: float, previous: float) -> dict:
    current = float(current or 0)
    previous = float(previous or 0)
    absolute = current - previous
    if previous == 0:
        percent = 100.0 if current > 0 else 0.0
    else:
        percent = round((absolute / previous) * 100, 1)
    return {"current": current, "previous": previous, "absolute": round(absolute, 4), "percent": percent}


def _attention_item(title: str, value: int | float, severity: str, path: str, detail: str = "") -> dict | None:
    if not value:
        return None
    rank = {"critical": 0, "high": 1, "medium": 2, "info": 3}.get(severity, 3)
    return {"title": title, "value": value, "severity": severity, "path": path, "detail": detail, "rank": rank}


class EventPayload(BaseModel):
    session_id:  Optional[str] = Field(default=None, max_length=128)
    customer_id: Optional[str] = Field(default=None, max_length=128)
    event_type:  str = Field(..., max_length=64)
    label:       Optional[str] = Field(default=None, max_length=256)
    meta:        Optional[str] = Field(default=None, max_length=512)
    # tree-specific (kept for compat)
    topic_id:    Optional[str] = None
    article_id:  Optional[int] = None


@router.post("/analytics/click")
@limiter.limit("120/minute")
async def track_event(request: Request, payload: EventPayload):
    # Open endpoint — widget fires this without an API key
    if payload.event_type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported event type")
    await log_widget_event(
        session_id=payload.session_id or "",
        customer_id=payload.customer_id or "",
        event_type=payload.event_type,
        label=payload.label or "",
        meta=payload.meta or "",
    )
    if payload.event_type == "tree_click" and payload.topic_id:
        await log_tree_click(
            session_id=payload.session_id or "",
            customer_id=payload.customer_id or "",
            topic_id=payload.topic_id,
            topic_label=payload.label or "",
            article_id=payload.article_id,
        )
    if payload.event_type in {"feedback_good", "feedback_bad"}:
        await log_message_feedback(
            session_id=payload.session_id or "",
            customer_id=payload.customer_id or "",
            channel="web",
            turn_id="",
            score="good" if payload.event_type == "feedback_good" else "bad",
            source=payload.label or "",
            reason=payload.meta or "",
        )
    return {"ok": True}


@router.get("/analytics/dashboard")
async def get_dashboard(days: int = Query(default=30, ge=1, le=365), _: None = Depends(verify_api_key)):
    pool = await get_db_pool()
    now = datetime.now(timezone.utc)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    previous_since = since - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    async with pool.acquire() as conn:
        # ── totals ────────────────────────────────────────────────────────
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(DISTINCT session_id)          AS total_sessions,
                COUNT(*)                             AS total_messages,
                ROUND(AVG(confidence)::numeric, 3)  AS avg_confidence,
                SUM(CASE WHEN escalated THEN 1 ELSE 0 END) AS escalations
            FROM conversation_logs
            WHERE created_at >= $1
            """,
            since,
        )
        total_sessions  = row["total_sessions"] or 0
        total_messages  = row["total_messages"] or 0
        avg_confidence  = float(row["avg_confidence"] or 0)
        escalations     = row["escalations"] or 0
        escalation_rate = round(escalations / total_messages, 4) if total_messages else 0

        # ── source breakdown ──────────────────────────────────────────────
        src_rows = await conn.fetch(
            """
            SELECT source, COUNT(*) AS cnt
            FROM conversation_logs
            WHERE created_at >= $1 AND source IS NOT NULL AND source != ''
            GROUP BY source
            ORDER BY cnt DESC
            """,
            since,
        )
        source_breakdown = {r["source"]: r["cnt"] for r in src_rows}

        # ── top tree topics ───────────────────────────────────────────────
        topic_rows = await conn.fetch(
            """
            SELECT topic_label, topic_id,
                   COUNT(*) AS clicks,
                   COUNT(CASE WHEN article_id IS NOT NULL THEN 1 END) AS leaf_clicks
            FROM tree_clicks
            WHERE created_at >= $1
            GROUP BY topic_label, topic_id
            ORDER BY clicks DESC
            LIMIT 20
            """,
            since,
        )
        top_tree_topics = [
            {
                "topic_id":    r["topic_id"],
                "topic_label": r["topic_label"],
                "clicks":      r["clicks"],
                "leaf_clicks": r["leaf_clicks"],
            }
            for r in topic_rows
        ]

        # ── daily volume (last N days) ────────────────────────────────────
        daily_rows = await conn.fetch(
            """
            SELECT DATE(created_at AT TIME ZONE 'UTC') AS day,
                   COUNT(*) AS messages,
                   COUNT(DISTINCT session_id) AS sessions
            FROM conversation_logs
            WHERE created_at >= $1
            GROUP BY day
            ORDER BY day
            """,
            since,
        )
        daily_volume = [
            {
                "date":     str(r["day"]),
                "messages": r["messages"],
                "sessions": r["sessions"],
            }
            for r in daily_rows
        ]

        # ── hourly distribution (what time of day is busiest) ────────────
        hourly_rows = await conn.fetch(
            """
            SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hour,
                   COUNT(*) AS messages
            FROM conversation_logs
            WHERE created_at >= $1
            GROUP BY hour
            ORDER BY hour
            """,
            since,
        )
        hourly_distribution = [
            {"hour": r["hour"], "messages": r["messages"]}
            for r in hourly_rows
        ]

        # ── widget event type breakdown ───────────────────────────────────
        event_rows = await conn.fetch(
            """
            SELECT event_type, COUNT(*) AS cnt
            FROM widget_events
            WHERE created_at >= $1
            GROUP BY event_type
            ORDER BY cnt DESC
            """,
            since,
        )
        event_breakdown = [
            {"event_type": r["event_type"], "count": r["cnt"]}
            for r in event_rows
        ]

        feedback_row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN score = 'good' THEN 1 ELSE 0 END) AS good,
                SUM(CASE WHEN score = 'bad' THEN 1 ELSE 0 END) AS bad
            FROM message_feedback
            WHERE created_at >= $1
            """,
            since,
        )
        feedback_total = feedback_row["total"] or 0
        feedback_good = feedback_row["good"] or 0
        feedback_bad = feedback_row["bad"] or 0

        outcome_row = await conn.fetchrow(
            """
            SELECT
                ROUND(AVG(time_to_accept_seconds)::numeric, 1) AS avg_accept,
                ROUND(AVG(time_to_resolution_seconds)::numeric, 1) AS avg_resolution,
                COUNT(*) AS resolved
            FROM session_outcomes
            WHERE created_at >= $1 OR resolved_at >= $1
            """,
            since,
        )
        avg_time_to_accept_seconds = float(outcome_row["avg_accept"] or 0)
        avg_time_to_resolution_seconds = float(outcome_row["avg_resolution"] or 0)
        resolved_sessions = outcome_row["resolved"] or 0

        gap_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS gaps
            FROM message_insights
            WHERE created_at >= $1 AND is_knowledge_gap = TRUE
            """,
            since,
        )
        knowledge_gaps = gap_row["gaps"] or 0

        cost_row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(estimated_cost), 0) AS cost,
                   COALESCE(SUM(total_tokens), 0) AS tokens
            FROM llm_usage_logs
            WHERE created_at >= $1
            """,
            since,
        )
        estimated_ai_cost = float(cost_row["cost"] or 0)
        llm_total_tokens = int(cost_row["tokens"] or 0)

        top_intent_rows = await conn.fetch(
            """
            SELECT intent, COUNT(*) AS count
            FROM message_insights
            WHERE created_at >= $1 AND intent IS NOT NULL AND intent != ''
            GROUP BY intent
            ORDER BY count DESC
            LIMIT 8
            """,
            since,
        )
        top_intents = [{"intent": r["intent"], "count": r["count"]} for r in top_intent_rows]

        handoff_rows = await conn.fetch(
            """
            SELECT COALESCE(NULLIF(handoff_reason, ''), 'unknown') AS reason, COUNT(*) AS count
            FROM session_outcomes
            WHERE created_at >= $1 AND handoff_reason IS NOT NULL
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 8
            """,
            since,
        )
        handoff_reasons = [{"reason": r["reason"], "count": r["count"]} for r in handoff_rows]

        case_row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed')) AS open_cases,
                COUNT(*) FILTER (WHERE status = 'escalated') AS escalated_cases,
                COUNT(*) FILTER (WHERE status IN ('resolved','closed')) AS resolved_cases,
                COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed') AND sla_status = 'at_risk') AS cases_at_risk,
                COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed') AND sla_status = 'breached') AS cases_breached,
                COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed') AND sla_due_at < NOW()) AS cases_overdue,
                ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))) FILTER (WHERE resolved_at IS NOT NULL)::numeric, 1) AS avg_case_resolution
            FROM support_cases
            WHERE created_at >= $1 OR updated_at >= $1 OR resolved_at >= $1
            """,
            since,
        )
        case_dept_rows = await conn.fetch(
            """
            SELECT department, COUNT(*) AS count
            FROM support_cases
            WHERE created_at >= $1 OR updated_at >= $1
            GROUP BY department
            ORDER BY count DESC
            LIMIT 8
            """,
            since,
        )

        # ── recent conversations ──────────────────────────────────────────
        recent_rows = await conn.fetch(
            """
            SELECT session_id, channel, customer_message, source,
                   ROUND(confidence::numeric, 2) AS confidence,
                   escalated, created_at
            FROM conversation_logs
            WHERE created_at >= $1
            ORDER BY created_at DESC
            LIMIT 50
            """,
            since,
        )
        recent = [
            {
                "session_id":       r["session_id"],
                "channel":          r["channel"],
                "customer_message": r["customer_message"],
                "source":           r["source"],
                "confidence":       float(r["confidence"] or 0),
                "escalated":        r["escalated"],
                "created_at":       r["created_at"].isoformat(),
            }
            for r in recent_rows
        ]

        period_row = await conn.fetchrow(
            """
            SELECT
                COUNT(DISTINCT session_id) AS sessions,
                COUNT(*) AS messages,
                SUM(CASE WHEN escalated THEN 1 ELSE 0 END) AS escalations
            FROM conversation_logs
            WHERE created_at >= $1 AND created_at < $2
            """,
            previous_since, since,
        )
        previous_sessions = period_row["sessions"] or 0
        previous_messages = period_row["messages"] or 0
        previous_escalations = period_row["escalations"] or 0
        previous_escalation_rate = previous_escalations / previous_messages if previous_messages else 0
        previous_deflection_rate = (previous_sessions - previous_escalations) / previous_sessions if previous_sessions else 0

        previous_feedback = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN score = 'good' THEN 1 ELSE 0 END) AS good
            FROM message_feedback
            WHERE created_at >= $1 AND created_at < $2
            """,
            previous_since, since,
        )
        previous_feedback_total = previous_feedback["total"] or 0
        previous_feedback_good = previous_feedback["good"] or 0
        previous_feedback_rate = previous_feedback_good / previous_feedback_total if previous_feedback_total else 0

        today_row = await conn.fetchrow(
            """
            SELECT
                COUNT(DISTINCT session_id) AS sessions,
                COUNT(*) AS messages,
                SUM(CASE WHEN escalated THEN 1 ELSE 0 END) AS escalations
            FROM conversation_logs
            WHERE created_at >= $1
            """,
            today_start,
        )
        yesterday_row = await conn.fetchrow(
            """
            SELECT
                COUNT(DISTINCT session_id) AS sessions,
                COUNT(*) AS messages,
                SUM(CASE WHEN escalated THEN 1 ELSE 0 END) AS escalations
            FROM conversation_logs
            WHERE created_at >= $1 AND created_at < $2
            """,
            yesterday_start, today_start,
        )
        today_cases = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = ANY($1::text[])) AS open_cases,
                COUNT(*) FILTER (WHERE department = 'suggestions' AND created_at >= $2) AS new_suggestions
            FROM support_cases
            """,
            list(ACTIVE_CASE_STATUSES), today_start,
        )
        yesterday_cases = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = ANY($1::text[])) AS open_cases,
                COUNT(*) FILTER (
                    WHERE department = 'suggestions'
                      AND created_at >= $2
                      AND created_at < $3
                ) AS new_suggestions
            FROM support_cases
            """,
            list(ACTIVE_CASE_STATUSES), yesterday_start, today_start,
        )

        queue_row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'PENDING_HANDOFF') AS pending_handoffs,
                COUNT(*) FILTER (WHERE status = 'HUMAN_ACTIVE') AS human_active,
                COALESCE(MAX(EXTRACT(EPOCH FROM (NOW() - updated_at))) FILTER (WHERE status = 'PENDING_HANDOFF'), 0) AS oldest_wait_seconds,
                COALESCE(AVG(EXTRACT(EPOCH FROM (NOW() - updated_at))) FILTER (WHERE status = 'PENDING_HANDOFF'), 0) AS avg_wait_seconds
            FROM sessions
            WHERE status IN ('ACTIVE', 'PENDING_HANDOFF', 'HUMAN_ACTIVE')
            """
        )

        ops_case_row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = ANY($1::text[])) AS open,
                COUNT(*) FILTER (WHERE status = ANY($1::text[]) AND owner IS NULL) AS unassigned,
                COUNT(*) FILTER (WHERE status = ANY($1::text[]) AND sla_status = 'breached') AS breached,
                COUNT(*) FILTER (WHERE status = ANY($1::text[]) AND sla_status = 'at_risk') AS at_risk
            FROM support_cases
            """,
            list(ACTIVE_CASE_STATUSES),
        )
        case_owner_rows = await conn.fetch(
            """
            SELECT COALESCE(owner, 'Unassigned') AS owner, COUNT(*) AS count
            FROM support_cases
            WHERE status = ANY($1::text[])
            GROUP BY COALESCE(owner, 'Unassigned')
            ORDER BY count DESC
            LIMIT 8
            """,
            list(ACTIVE_CASE_STATUSES),
        )
        ops_case_dept_rows = await conn.fetch(
            """
            SELECT department, COUNT(*) AS count
            FROM support_cases
            WHERE status = ANY($1::text[])
            GROUP BY department
            ORDER BY count DESC
            LIMIT 8
            """,
            list(ACTIVE_CASE_STATUSES),
        )

        suggestion_row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status IN ('open','pending')) AS new,
                COUNT(*) FILTER (WHERE status = ANY($1::text[]) AND owner IS NULL) AS unassigned
            FROM support_cases
            WHERE department = 'suggestions'
            """,
            list(ACTIVE_CASE_STATUSES),
        )
        suggestion_channel_rows = await conn.fetch(
            """
            SELECT COALESCE(channel, 'unknown') AS channel, COUNT(*) AS count
            FROM support_cases
            WHERE department = 'suggestions'
            GROUP BY COALESCE(channel, 'unknown')
            ORDER BY count DESC
            LIMIT 8
            """
        )

    today = {
        "messages": today_row["messages"] or 0,
        "sessions": today_row["sessions"] or 0,
        "escalations": today_row["escalations"] or 0,
        "open_cases": today_cases["open_cases"] or 0,
        "new_suggestions": today_cases["new_suggestions"] or 0,
    }
    previous_period = {
        "messages": previous_messages,
        "sessions": previous_sessions,
        "escalations": previous_escalations,
        "escalation_rate": round(previous_escalation_rate, 4),
        "deflection_rate": round(previous_deflection_rate, 4),
        "feedback_positive_rate": round(previous_feedback_rate, 4),
        "today_messages": yesterday_row["messages"] or 0,
        "today_sessions": yesterday_row["sessions"] or 0,
        "today_escalations": yesterday_row["escalations"] or 0,
        "open_cases": yesterday_cases["open_cases"] or 0,
        "new_suggestions": yesterday_cases["new_suggestions"] or 0,
    }
    queue = {
        "pending_handoffs": queue_row["pending_handoffs"] or 0,
        "human_active": queue_row["human_active"] or 0,
        "oldest_wait_seconds": float(queue_row["oldest_wait_seconds"] or 0),
        "avg_wait_seconds": float(queue_row["avg_wait_seconds"] or 0),
    }
    cases = {
        "open": ops_case_row["open"] or 0,
        "unassigned": ops_case_row["unassigned"] or 0,
        "breached": ops_case_row["breached"] or 0,
        "at_risk": ops_case_row["at_risk"] or 0,
        "by_owner": [dict(r) for r in case_owner_rows],
        "by_department": [dict(r) for r in ops_case_dept_rows],
    }
    suggestions = {
        "new": suggestion_row["new"] or 0,
        "unassigned": suggestion_row["unassigned"] or 0,
        "by_channel": [dict(r) for r in suggestion_channel_rows],
    }
    feedback_positive_rate = round(feedback_good / feedback_total, 4) if feedback_total else 0
    deflection_rate = round((total_sessions - escalations) / total_sessions, 4) if total_sessions else 0
    deltas = {
        "messages": _pct_delta(total_messages, previous_messages),
        "sessions": _pct_delta(total_sessions, previous_sessions),
        "escalation_rate": _pct_delta(escalation_rate, previous_escalation_rate),
        "deflection_rate": _pct_delta(deflection_rate, previous_deflection_rate),
        "feedback_positive_rate": _pct_delta(feedback_positive_rate, previous_feedback_rate),
        "today_messages": _pct_delta(today["messages"], previous_period["today_messages"]),
        "today_sessions": _pct_delta(today["sessions"], previous_period["today_sessions"]),
    }
    attention_items = [
        _attention_item("SLA breached", cases["breached"], "critical", "/cases", "Cases are past due"),
        _attention_item("SLA at risk", cases["at_risk"], "high", "/cases", "Cases are close to deadline"),
        _attention_item("Pending handoffs", queue["pending_handoffs"], "high", "/queue", "Customers are waiting for agents"),
        _attention_item("Unassigned cases", cases["unassigned"], "medium", "/cases", "Cases need an owner"),
        _attention_item("Unassigned suggestions", suggestions["unassigned"], "medium", "/suggestions", "Feedback needs review"),
        _attention_item("Knowledge gaps", knowledge_gaps, "medium", "/gaps", "Questions need better answers"),
        _attention_item("Bad feedback", feedback_bad, "medium", "/reports", "Customers marked answers as bad"),
    ]
    attention_items = sorted([item for item in attention_items if item], key=lambda item: item["rank"])[:6]

    return {
        "period_days":          days,
        "total_sessions":       total_sessions,
        "total_messages":       total_messages,
        "avg_confidence":       avg_confidence,
        "escalation_rate":      escalation_rate,
        "escalations":          escalations,
        "source_breakdown":     source_breakdown,
        "top_tree_topics":      top_tree_topics,
        "daily_volume":         daily_volume,
        "hourly_distribution":  hourly_distribution,
        "event_breakdown":      event_breakdown,
        "feedback_total":       feedback_total,
        "feedback_good":        feedback_good,
        "feedback_bad":         feedback_bad,
        "feedback_positive_rate": feedback_positive_rate,
        "resolved_sessions":    resolved_sessions,
        "avg_time_to_accept_seconds": avg_time_to_accept_seconds,
        "avg_time_to_resolution_seconds": avg_time_to_resolution_seconds,
        "deflection_rate":      deflection_rate,
        "knowledge_gaps":       knowledge_gaps,
        "estimated_ai_cost":    round(estimated_ai_cost, 6),
        "llm_total_tokens":     llm_total_tokens,
        "top_intents":          top_intents,
        "handoff_reasons":      handoff_reasons,
        "case_open":            case_row["open_cases"] or 0,
        "case_escalated":       case_row["escalated_cases"] or 0,
        "case_resolved":        case_row["resolved_cases"] or 0,
        "case_at_risk":         case_row["cases_at_risk"] or 0,
        "case_breached":        case_row["cases_breached"] or 0,
        "case_overdue":         case_row["cases_overdue"] or 0,
        "avg_case_resolution_seconds": float(case_row["avg_case_resolution"] or 0),
        "case_department_breakdown": [dict(r) for r in case_dept_rows],
        "recent_conversations": recent,
        "today": today,
        "previous_period": previous_period,
        "deltas": deltas,
        "queue": queue,
        "cases": cases,
        "suggestions": suggestions,
        "attention_items": attention_items,
    }


@router.get("/analytics/reports")
async def get_reports(
    days: int = Query(default=30, ge=1, le=365),
    channel: Optional[str] = None,
    _: None = Depends(verify_api_key),
):
    pool = await get_db_pool()
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # $2 = channel filter (None means no filter — Postgres IS NULL check skips it)
    ch = channel or None

    async with pool.acquire() as conn:
        gap_rows = await conn.fetch(
            """
            SELECT message_text, intent, sub_intent, gap_reason, channel, created_at
            FROM message_insights
            WHERE created_at >= $1
              AND is_knowledge_gap = TRUE
              AND ($2::text IS NULL OR channel = $2)
            ORDER BY created_at DESC
            LIMIT 100
            """,
            since, ch,
        )
        intent_rows = await conn.fetch(
            """
            SELECT intent, sub_intent, COUNT(*) AS count
            FROM message_insights
            WHERE created_at >= $1
              AND ($2::text IS NULL OR channel = $2)
            GROUP BY intent, sub_intent
            ORDER BY count DESC
            LIMIT 30
            """,
            since, ch,
        )
        handoff_rows = await conn.fetch(
            """
            SELECT COALESCE(NULLIF(handoff_reason, ''), 'unknown') AS reason, COUNT(*) AS count
            FROM session_outcomes
            WHERE created_at >= $1 AND handoff_reason IS NOT NULL
            GROUP BY reason
            ORDER BY count DESC
            """,
            since,
        )
        outcome_rows = await conn.fetch(
            """
            SELECT status, issue_category, root_cause, COUNT(*) AS count,
                   ROUND(AVG(time_to_resolution_seconds)::numeric, 1) AS avg_resolution
            FROM session_outcomes
            WHERE (created_at >= $1 OR resolved_at >= $1)
            GROUP BY status, issue_category, root_cause
            ORDER BY count DESC
            LIMIT 30
            """,
            since,
        )
        cost_rows = await conn.fetch(
            """
            SELECT model, operation, SUM(prompt_tokens) AS prompt_tokens,
                   SUM(completion_tokens) AS completion_tokens,
                   SUM(total_tokens) AS total_tokens,
                   ROUND(SUM(estimated_cost)::numeric, 6) AS estimated_cost
            FROM llm_usage_logs
            WHERE created_at >= $1
            GROUP BY model, operation
            ORDER BY estimated_cost DESC
            """,
            since,
        )
        channel_rows = await conn.fetch(
            """
            SELECT channel, COUNT(*) AS messages
            FROM conversation_logs
            WHERE created_at >= $1
            GROUP BY channel
            ORDER BY messages DESC
            """,
            since,
        )
        bad_feedback_rows = await conn.fetch(
            """
            SELECT cl.session_id, cl.customer_message, cl.agent_response,
                   cl.source, mf.reason, mf.created_at
            FROM message_feedback mf
            JOIN conversation_logs cl ON cl.session_id = mf.session_id
            WHERE mf.created_at >= $1 AND mf.score = 'bad'
              AND ($2::text IS NULL OR cl.channel = $2)
            ORDER BY mf.created_at DESC
            LIMIT 50
            """,
            since, ch,
        )

    return {
        "period_days": days,
        "channel_filter": channel,
        "knowledge_gaps": [
            {
                "message_text": r["message_text"],
                "intent": r["intent"],
                "sub_intent": r["sub_intent"],
                "gap_reason": r["gap_reason"],
                "channel": r["channel"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in gap_rows
        ],
        "intents": [dict(r) for r in intent_rows],
        "handoffs": [dict(r) for r in handoff_rows],
        "outcomes": [
            {
                "status": r["status"],
                "issue_category": r["issue_category"],
                "root_cause": r["root_cause"],
                "count": r["count"],
                "avg_resolution": float(r["avg_resolution"] or 0),
            }
            for r in outcome_rows
        ],
        "costs": [
            {
                "model": r["model"],
                "operation": r["operation"],
                "prompt_tokens": int(r["prompt_tokens"] or 0),
                "completion_tokens": int(r["completion_tokens"] or 0),
                "total_tokens": int(r["total_tokens"] or 0),
                "estimated_cost": float(r["estimated_cost"] or 0),
            }
            for r in cost_rows
        ],
        "channels": [dict(r) for r in channel_rows],
        "bad_feedback": [
            {
                "session_id": r["session_id"],
                "customer_message": r["customer_message"],
                "agent_response": r["agent_response"],
                "source": r["source"],
                "reason": r["reason"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in bad_feedback_rows
        ],
    }


@router.get("/analytics/ratings")
async def get_ratings(_: None = Depends(verify_api_key)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT (metadata->>'rating')::int AS rating
            FROM sessions
            WHERE metadata ? 'rating'
              AND (metadata->>'rating')::int BETWEEN 1 AND 5
            """
        )
    rated = [r["rating"] for r in rows]
    dist = {str(i): 0 for i in range(1, 6)}
    for score in rated:
        dist[str(score)] += 1
    avg = round(sum(rated) / len(rated), 2) if rated else None
    return {"avg_rating": avg, "total_rated": len(rated), "distribution": dist}
