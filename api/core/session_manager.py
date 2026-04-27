import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis

from config import settings
from core.logger import log_turn
from models.session import ConversationTurn, Session, SessionStatus

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None
SESSION_TTL = 3600 * 24  # 24 hours


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
    r = get_redis()
    if session_id:
        data = await r.get(f"session:{session_id}")
        if data:
            return Session(**json.loads(data))

    new_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    session = Session(
        session_id=new_id,
        customer_id=customer_id,
        channel=channel,
        created_at=now,
        updated_at=now,
    )
    await save_session(session)
    return session


async def save_session(session: Session) -> None:
    r = get_redis()
    await r.setex(
        f"session:{session.session_id}", SESSION_TTL, session.model_dump_json()
    )


async def get_session(session_id: str) -> Optional[Session]:
    r = get_redis()
    data = await r.get(f"session:{session_id}")
    if data:
        return Session(**json.loads(data))
    return None


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
    pending = []
    async for key in r.scan_iter("session:*"):
        data = await r.get(key)
        if data:
            try:
                s = Session(**json.loads(data))
                if s.status == SessionStatus.pending_handoff:
                    pending.append(s)
            except Exception:
                pass
    return pending


async def get_all_sessions(status_filter: Optional[str] = None) -> List[Session]:
    r = get_redis()
    sessions = []
    async for key in r.scan_iter("session:*"):
        data = await r.get(key)
        if data:
            try:
                s = Session(**json.loads(data))
                if status_filter is None or s.status.value == status_filter:
                    sessions.append(s)
            except Exception:
                pass
    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions
