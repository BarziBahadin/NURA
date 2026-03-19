import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis

from config import settings
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


async def append_turn(
    session: Session, role: str, message: str, confidence: float = 0.0
) -> None:
    turn = ConversationTurn(
        role=role,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=confidence if role == "agent" else None,
    )
    session.history.append(turn)
    session.updated_at = datetime.now(timezone.utc).isoformat()
    await save_session(session)


async def get_pending_handoff_sessions() -> List[Session]:
    r = get_redis()
    keys = await r.keys("session:*")
    pending = []
    for key in keys:
        data = await r.get(key)
        if data:
            try:
                s = Session(**json.loads(data))
                if s.status == SessionStatus.pending_handoff:
                    pending.append(s)
            except Exception:
                pass
    return pending
