import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import verify_api_key
from core.logger import log_message_feedback, log_tree_click, log_widget_event
from core.session_manager import get_all_sessions
from db.postgres import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

ALLOWED_EVENT_TYPES = {
    "chat_open", "chat_close", "lang_switch", "send_message",
    "tree_click", "tree_back", "tree_home", "followup_yes",
    "followup_no", "feedback_good", "feedback_bad", "direct_to_agent",
}


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
async def get_dashboard(days: int = 30, _: None = Depends(verify_api_key)):
    pool = await get_db_pool()
    since = datetime.now(timezone.utc) - timedelta(days=days)

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

        # ── recent conversations ──────────────────────────────────────────
        recent_rows = await conn.fetch(
            """
            SELECT session_id, channel, customer_message, source,
                   ROUND(confidence::numeric, 2) AS confidence,
                   escalated, created_at
            FROM conversation_logs
            ORDER BY created_at DESC
            LIMIT 50
            """,
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
        "feedback_positive_rate": round(feedback_good / feedback_total, 4) if feedback_total else 0,
        "resolved_sessions":    resolved_sessions,
        "avg_time_to_accept_seconds": avg_time_to_accept_seconds,
        "avg_time_to_resolution_seconds": avg_time_to_resolution_seconds,
        "deflection_rate":      round((total_sessions - escalations) / total_sessions, 4) if total_sessions else 0,
        "knowledge_gaps":       knowledge_gaps,
        "estimated_ai_cost":    round(estimated_ai_cost, 6),
        "llm_total_tokens":     llm_total_tokens,
        "top_intents":          top_intents,
        "handoff_reasons":      handoff_reasons,
        "recent_conversations": recent,
    }


@router.get("/analytics/reports")
async def get_reports(days: int = 30, _: None = Depends(verify_api_key)):
    pool = await get_db_pool()
    since = datetime.now(timezone.utc) - timedelta(days=days)

    async with pool.acquire() as conn:
        gap_rows = await conn.fetch(
            """
            SELECT message_text, intent, sub_intent, gap_reason, created_at
            FROM message_insights
            WHERE created_at >= $1 AND is_knowledge_gap = TRUE
            ORDER BY created_at DESC
            LIMIT 50
            """,
            since,
        )
        intent_rows = await conn.fetch(
            """
            SELECT intent, sub_intent, COUNT(*) AS count
            FROM message_insights
            WHERE created_at >= $1
            GROUP BY intent, sub_intent
            ORDER BY count DESC
            LIMIT 30
            """,
            since,
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
            WHERE created_at >= $1 OR resolved_at >= $1
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

    return {
        "period_days": days,
        "knowledge_gaps": [
            {
                "message_text": r["message_text"],
                "intent": r["intent"],
                "sub_intent": r["sub_intent"],
                "gap_reason": r["gap_reason"],
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
    }


@router.get("/analytics/ratings")
async def get_ratings(_: None = Depends(verify_api_key)):
    sessions = await get_all_sessions()
    rated = [s.metadata["rating"] for s in sessions if "rating" in s.metadata]
    dist = {str(i): 0 for i in range(1, 6)}
    for r in rated:
        if 1 <= r <= 5:
            dist[str(r)] += 1
    avg = round(sum(rated) / len(rated), 2) if rated else None
    return {"avg_rating": avg, "total_rated": len(rated), "distribution": dist}
