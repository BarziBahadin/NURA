import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from core.auth import is_valid_api_key, verify_api_key
from core.session_manager import append_turn, get_all_sessions, get_session, publish_session_event, save_session
from models.session import SessionStatus

router = APIRouter()


def verify_session_access(request: Request, session) -> None:
    if is_valid_api_key(request):
        return
    supplied = request.query_params.get("session_token") or request.headers.get("X-Session-Token", "")
    expected = session.metadata.get("customer_token", "")
    if not expected or supplied != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/session/{session_id}")
async def get_session_route(
    session_id: str, _: None = Depends(verify_api_key)
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/session/{session_id}")
async def close_session(session_id: str, _: None = Depends(verify_api_key)):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.resolved
    await save_session(session)
    await publish_session_event(session_id, {"type": "status", "status": "RESOLVED"})
    return {"message": "Session closed", "session_id": session_id}


@router.post("/session/{session_id}/resolve")
async def resolve_session(session_id: str, _: None = Depends(verify_api_key)):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.resolved
    await save_session(session)
    await publish_session_event(session_id, {"type": "status", "status": "RESOLVED"})
    return {"ok": True, "session_id": session_id}


@router.get("/sessions/list")
async def list_sessions(
    status: Optional[str] = None,
    limit: int = 50,
    _: None = Depends(verify_api_key),
):
    sessions = await get_all_sessions(status_filter=status)
    return {
        "total": len(sessions),
        "sessions": [s.model_dump() for s in sessions[:limit]],
    }


@router.get("/queue")
async def get_queue(_: None = Depends(verify_api_key)):
    all_sessions = await get_all_sessions()
    active = [
        s for s in all_sessions
        if s.status in (SessionStatus.pending_handoff, SessionStatus.human_active)
    ]
    active.sort(key=lambda s: s.updated_at)
    return {"pending": len(active), "sessions": [s.model_dump() for s in active]}


class AgentMessageBody(BaseModel):
    message: str
    agent_name: str = "Agent"


@router.post("/session/{session_id}/agent-message")
async def send_agent_message(
    session_id: str,
    body: AgentMessageBody,
    _: None = Depends(verify_api_key),
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.human_active:
        raise HTTPException(status_code=409, detail="Session is not in HUMAN_ACTIVE state")
    await append_turn(session, role="agent", message=body.message, source="human")
    return {"ok": True}


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str, request: Request, since: str = ""):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    verify_session_access(request, session)
    turns = session.history
    if since:
        turns = [t for t in turns if t.timestamp > since]
    return {
        "turns": [t.model_dump() for t in turns],
        "status": session.status.value,
    }


@router.get("/session/{session_id}/stream")
async def session_stream(session_id: str, request: Request):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    verify_session_access(request, session)

    from core.session_manager import get_redis

    async def event_generator():
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"session:events:{session_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    yield {"data": msg["data"]}
        finally:
            await pubsub.unsubscribe(f"session:events:{session_id}")
            await pubsub.aclose()

    return EventSourceResponse(event_generator())
