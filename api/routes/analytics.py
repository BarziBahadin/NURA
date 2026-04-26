import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import verify_api_key
from core.logger import log_tree_click, log_widget_event
from db.postgres import get_db_pool
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class EventPayload(BaseModel):
    session_id:  Optional[str] = None
    customer_id: Optional[str] = None
    event_type:  str
    label:       Optional[str] = None
    meta:        Optional[str] = None
    # tree-specific (kept for compat)
    topic_id:    Optional[str] = None
    article_id:  Optional[int] = None


@router.post("/analytics/click")
async def track_event(payload: EventPayload):
    # Open endpoint — widget fires this without an API key
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
        "recent_conversations": recent,
    }
