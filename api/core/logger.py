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
) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_logs
                  (session_id, customer_id, channel, customer_message,
                   agent_response, confidence, escalated, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                session_id,
                customer_id,
                channel,
                customer_message,
                agent_response,
                confidence,
                escalated,
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Failed to log conversation: {e}")


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
