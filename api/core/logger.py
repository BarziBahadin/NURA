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
