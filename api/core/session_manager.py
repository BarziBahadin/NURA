import json
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis

from config import settings
from core.logger import log_turn
from db.postgres import get_db_pool
from models.session import ConversationTurn, Session, SessionStatus

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None
SESSION_TTL = 3600 * 24  # 24 hours
HUMAN_SESSION_TTL = 3600 * 24 * 7  # one week for live handoff recovery
CUSTOMER_TOKEN_KEY = "customer_token"


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _redis_client


async def get_or_create_session(
    session_id: Optional[str], customer_id: str, channel: str
) -> Session:
    if session_id:
        session = await get_session(session_id)
        if session:
            return session

    new_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    session = Session(
        session_id=new_id,
        customer_id=customer_id,
        channel=channel,
        created_at=now,
        updated_at=now,
    )
    session.metadata[CUSTOMER_TOKEN_KEY] = secrets.token_urlsafe(32)
    await save_session(session)
    return session


def get_customer_token(session: Session) -> str:
    token = session.metadata.get(CUSTOMER_TOKEN_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session.metadata[CUSTOMER_TOKEN_KEY] = token
    return token


async def save_session(session: Session) -> None:
    ttl = HUMAN_SESSION_TTL if session.status in (
        SessionStatus.pending_handoff,
        SessionStatus.human_active,
    ) else SESSION_TTL
    session_json = session.model_dump_json()

    r = get_redis()
    try:
        await r.setex(f"session:{session.session_id}", ttl, session_json)
    except Exception as e:
        logger.error(f"Failed to save session {session.session_id} to Redis: {e}")

    await persist_session(session)


async def get_session(session_id: str) -> Optional[Session]:
    r = get_redis()
    try:
        data = await r.get(f"session:{session_id}")
        if data:
            return Session(**json.loads(data))
    except Exception as e:
        logger.error(f"Failed to read session {session_id} from Redis: {e}")

    session = await load_session_from_db(session_id)
    if session:
        try:
            ttl = HUMAN_SESSION_TTL if session.status in (
                SessionStatus.pending_handoff,
                SessionStatus.human_active,
            ) else SESSION_TTL
            await r.setex(f"session:{session.session_id}", ttl, session.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to restore session {session_id} into Redis: {e}")
    return session


async def persist_session(session: Session) -> None:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions
                  (session_id, customer_id, channel, status, history,
                   failure_count, negative_score, metadata, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8::jsonb,$9,$10)
                ON CONFLICT (session_id) DO UPDATE SET
                  customer_id=EXCLUDED.customer_id,
                  channel=EXCLUDED.channel,
                  status=EXCLUDED.status,
                  history=EXCLUDED.history,
                  failure_count=EXCLUDED.failure_count,
                  negative_score=EXCLUDED.negative_score,
                  metadata=EXCLUDED.metadata,
                  updated_at=EXCLUDED.updated_at
                """,
                session.session_id,
                session.customer_id,
                session.channel,
                session.status.value,
                json.dumps([turn.model_dump() for turn in session.history]),
                session.failure_count,
                session.negative_score,
                json.dumps(session.metadata),
                datetime.fromisoformat(session.created_at),
                datetime.fromisoformat(session.updated_at),
            )
    except Exception as e:
        logger.error(f"Failed to persist session {session.session_id} to Postgres: {e}")


async def load_session_from_db(session_id: str) -> Optional[Session]:
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT session_id, customer_id, channel, status, history,
                       failure_count, negative_score, metadata, created_at, updated_at
                FROM sessions
                WHERE session_id = $1
                """,
                session_id,
            )
    except Exception as e:
        logger.error(f"Failed to load session {session_id} from Postgres: {e}")
        return None

    if not row:
        return None

    history = row["history"]
    metadata = row["metadata"]
    if isinstance(history, str):
        history = json.loads(history)
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    return Session(
        session_id=row["session_id"],
        customer_id=row["customer_id"],
        channel=row["channel"],
        status=SessionStatus(row["status"]),
        history=[ConversationTurn(**turn) for turn in history],
        failure_count=row["failure_count"],
        negative_score=row["negative_score"],
        metadata=metadata,
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


async def publish_session_event(session_id: str, payload: dict) -> None:
    r = get_redis()
    try:
        await r.publish(f"session:events:{session_id}", json.dumps(payload))
    except Exception as e:
        logger.error(f"Failed to publish session event: {e}")


async def append_turn(
    session: Session, role: str, message: str, confidence: float = 0.0, source: str = "bot"
) -> None:
    turn = ConversationTurn(
        role=role,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=confidence if role == "agent" else None,
        source=source,
    )
    session.history.append(turn)
    session.updated_at = datetime.now(timezone.utc).isoformat()
    await save_session(session)
    await publish_session_event(session.session_id, {"type": "turn", "turn": turn.model_dump()})
    await log_turn(
        session_id=session.session_id,
        customer_id=session.customer_id,
        channel=session.channel,
        role=role,
        message=message,
        source=source,
        confidence=confidence if role == "agent" else None,
    )


async def get_pending_handoff_sessions() -> List[Session]:
    r = get_redis()
    pending: list[Session] = []
    seen: set[str] = set()
    try:
        async for key in r.scan_iter("session:*"):
            data = await r.get(key)
            if data:
                try:
                    s = Session(**json.loads(data))
                    if s.status == SessionStatus.pending_handoff:
                        pending.append(s)
                        seen.add(s.session_id)
                except Exception as e:
                    logger.warning(f"Skipping corrupt session at key {key}: {e}")
    except Exception as e:
        logger.error(f"Failed to scan pending sessions from Redis: {e}")
    pending.extend(await get_sessions_from_db(SessionStatus.pending_handoff, exclude=seen))
    return pending


async def get_all_sessions(status_filter: Optional[str] = None) -> List[Session]:
    r = get_redis()
    sessions: list[Session] = []
    seen: set[str] = set()
    try:
        async for key in r.scan_iter("session:*"):
            data = await r.get(key)
            if data:
                try:
                    s = Session(**json.loads(data))
                    if status_filter is None or s.status.value == status_filter:
                        sessions.append(s)
                        seen.add(s.session_id)
                except Exception as e:
                    logger.warning(f"Skipping corrupt session at key {key}: {e}")
    except Exception as e:
        logger.error(f"Failed to scan sessions from Redis: {e}")
    sessions.extend(await get_sessions_from_db(status_filter, exclude=seen))
    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions


async def get_sessions_from_db(
    status_filter: Optional[str | SessionStatus] = None,
    exclude: Optional[set[str]] = None,
) -> list[Session]:
    exclude = exclude or set()
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            if status_filter is None:
                rows = await conn.fetch(
                    """
                    SELECT session_id
                    FROM sessions
                    ORDER BY updated_at DESC
                    LIMIT 500
                    """
                )
            else:
                status = status_filter.value if isinstance(status_filter, SessionStatus) else status_filter
                rows = await conn.fetch(
                    """
                    SELECT session_id
                    FROM sessions
                    WHERE status = $1
                    ORDER BY updated_at DESC
                    LIMIT 500
                    """,
                    status,
                )
    except Exception as e:
        logger.error(f"Failed to list sessions from Postgres: {e}")
        return []

    sessions: list[Session] = []
    for row in rows:
        session_id = row["session_id"]
        if session_id in exclude:
            continue
        session = await load_session_from_db(session_id)
        if session:
            sessions.append(session)
    return sessions
