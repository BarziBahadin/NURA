import asyncio
import hmac
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from core.auth import has_admin_access, is_valid_api_key, verify_api_key
from core.logger import log_session_outcome
from core.session_manager import append_turn, get_all_sessions, get_session, publish_session_event, save_session
from models.session import SessionStatus

router = APIRouter()


class ResolveBody(BaseModel):
    status: str = Field(default="solved", max_length=64)
    issue_category: str = Field(default="", max_length=128)
    root_cause: str = Field(default="", max_length=512)
    resolution_notes: str = Field(default="", max_length=2048)
    resolved_by: str = Field(default="Agent", max_length=128)


def verify_session_access(request: Request, session) -> None:
    if has_admin_access(request):
        return
    supplied = request.query_params.get("session_token") or request.headers.get("X-Session-Token", "")
    expected = session.metadata.get("customer_token", "")
    if not expected or not hmac.compare_digest(supplied, expected):
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
async def resolve_session(
    session_id: str,
    body: ResolveBody | None = None,
    _: None = Depends(verify_api_key),
):
    body = body or ResolveBody()
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.resolved
    resolved_at = datetime.now(timezone.utc)
    created_at = datetime.fromisoformat(session.created_at)
    accepted_at = None
    if session.metadata.get("accepted_at"):
        try:
            accepted_at = datetime.fromisoformat(session.metadata["accepted_at"])
        except ValueError:
            accepted_at = None
    first_agent_response_at = None
    for turn in session.history:
        if turn.role == "agent" and turn.source == "human":
            try:
                first_agent_response_at = datetime.fromisoformat(turn.timestamp)
            except ValueError:
                first_agent_response_at = None
            break
    await save_session(session)
    await log_session_outcome(
        session_id=session_id,
        status=body.status,
        issue_category=body.issue_category,
        root_cause=body.root_cause,
        handoff_reason=session.metadata.get("handoff_reason", ""),
        resolution_notes=body.resolution_notes,
        resolved_by=body.resolved_by,
        accepted_at=accepted_at,
        resolved_at=resolved_at,
        first_agent_response_at=first_agent_response_at,
        time_to_accept_seconds=max(0, (accepted_at - created_at).total_seconds()) if accepted_at else None,
        time_to_resolution_seconds=max(0, (resolved_at - created_at).total_seconds()),
    )
    await publish_session_event(session_id, {"type": "status", "status": "RESOLVED"})
    return {"ok": True, "session_id": session_id}


@router.get("/sessions/list")
async def list_sessions(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
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


class RatingBody(BaseModel):
    score: int


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


@router.post("/session/{session_id}/typing")
async def session_typing(session_id: str, request: Request, sender: str = "agent"):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if sender == "agent":
        if not has_admin_access(request):
            raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        verify_session_access(request, session)
    await publish_session_event(session_id, {"type": "typing", "sender": sender})
    return {"ok": True}


@router.post("/session/{session_id}/rating")
async def rate_session(session_id: str, body: RatingBody, request: Request):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    verify_session_access(request, session)
    if not 1 <= body.score <= 5:
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")
    session.metadata["rating"] = body.score
    await save_session(session)
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
