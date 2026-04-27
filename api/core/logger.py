import logging
from datetime import datetime, timezone

from db.postgres import get_db_pool

logger = logging.getLogger(__name__)


async def log_conversation(
    session_id: str,
    customer_id: str,
    channel: str,
    customer_message: str,
    agent_response: str,
    confidence: float,
    escalated: bool,
    source: str = "",
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_logs
                  (session_id, customer_id, channel, customer_message,
                   agent_response, confidence, escalated, source, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                """,
                session_id,
                customer_id,
                channel,
                customer_message,
                agent_response,
                confidence,
                escalated,
                source,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log conversation: {e}")


async def log_tree_click(
    session_id: str,
    customer_id: str,
    topic_id: str,
    topic_label: str,
    article_id: int | None,
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tree_clicks
                  (session_id, customer_id, topic_id, topic_label, article_id, created_at)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                session_id,
                customer_id,
                topic_id,
                topic_label,
                article_id,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log tree click: {e}")


async def log_widget_event(
    session_id: str,
    customer_id: str,
    event_type: str,
    label: str = "",
    meta: str = "",
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO widget_events
                  (session_id, customer_id, event_type, label, meta, created_at)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                session_id,
                customer_id,
                event_type,
                label,
                meta,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log widget event: {e}")


async def log_turn(
    session_id: str,
    customer_id: str,
    channel: str,
    role: str,
    message: str,
    source: str,
    confidence: float = None,
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_turns
                  (session_id, customer_id, channel, role, message, source, confidence, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                session_id,
                customer_id,
                channel,
                role,
                message,
                source,
                confidence,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log turn: {e}")


async def log_message_feedback(
    session_id: str,
    customer_id: str,
    channel: str,
    turn_id: str,
    score: str,
    source: str = "",
    reason: str = "",
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO message_feedback
                  (session_id, customer_id, channel, turn_id, score, source, reason, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                session_id, customer_id, channel, turn_id, score, source, reason,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log message feedback: {e}")


async def log_session_outcome(
    session_id: str,
    status: str,
    issue_category: str = "",
    root_cause: str = "",
    handoff_reason: str = "",
    resolution_notes: str = "",
    resolved_by: str = "",
    accepted_at=None,
    resolved_at=None,
    first_agent_response_at=None,
    time_to_accept_seconds: float = None,
    time_to_resolution_seconds: float = None,
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO session_outcomes
                  (session_id, status, issue_category, root_cause, handoff_reason, resolution_notes,
                   resolved_by, accepted_at, resolved_at, first_agent_response_at,
                   time_to_accept_seconds, time_to_resolution_seconds, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (session_id) DO UPDATE SET
                  status=EXCLUDED.status, issue_category=EXCLUDED.issue_category,
                  root_cause=EXCLUDED.root_cause,
                  handoff_reason=COALESCE(NULLIF(EXCLUDED.handoff_reason, ''), session_outcomes.handoff_reason),
                  resolution_notes=EXCLUDED.resolution_notes,
                  resolved_by=EXCLUDED.resolved_by,
                  accepted_at=COALESCE(EXCLUDED.accepted_at, session_outcomes.accepted_at),
                  first_agent_response_at=COALESCE(EXCLUDED.first_agent_response_at, session_outcomes.first_agent_response_at),
                  resolved_at=COALESCE(EXCLUDED.resolved_at, session_outcomes.resolved_at),
                  time_to_accept_seconds=COALESCE(EXCLUDED.time_to_accept_seconds, session_outcomes.time_to_accept_seconds),
                  time_to_resolution_seconds=EXCLUDED.time_to_resolution_seconds
                """,
                session_id, status, issue_category or "", root_cause or "",
                handoff_reason or "", resolution_notes or "", resolved_by or "",
                accepted_at, resolved_at, first_agent_response_at,
                time_to_accept_seconds, time_to_resolution_seconds,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log session outcome: {e}")


async def log_message_insight(
    session_id: str,
    customer_id: str,
    channel: str,
    message_text: str,
    language: str = "unknown",
    intent: str = "unknown",
    sub_intent: str = "",
    sentiment: str = "neutral",
    confidence_bucket: str = "low",
    is_knowledge_gap: bool = False,
    gap_reason: str = "",
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO message_insights
                  (session_id, customer_id, channel, message_text, language,
                   intent, sub_intent, sentiment, confidence_bucket, is_knowledge_gap, gap_reason, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                """,
                session_id, customer_id, channel, message_text, language,
                intent, sub_intent, sentiment, confidence_bucket, is_knowledge_gap, gap_reason,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log message insight: {e}")


async def log_llm_usage(
    session_id: str,
    model: str,
    operation: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost: float,
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO llm_usage_logs
                  (session_id, model, operation, prompt_tokens, completion_tokens,
                   total_tokens, estimated_cost, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                session_id, model, operation, prompt_tokens, completion_tokens,
                prompt_tokens + completion_tokens, estimated_cost,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log LLM usage: {e}")


async def log_security_event(
    event_type: str, detail: str, ip: str = ""
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO security_logs (event_type, detail, ip, created_at)
                VALUES ($1,$2,$3,$4)
                """,
                event_type,
                detail,
                ip,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")
