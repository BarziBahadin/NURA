import hmac
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.auth import is_valid_api_key, verify_api_key
from core.logger import log_session_outcome
from core.session_manager import get_customer_token, get_or_create_session, get_session, save_session
from models.session import SessionStatus
from datetime import datetime, timezone

router = APIRouter()


def verify_handoff_access(request: Request, session) -> None:
    if is_valid_api_key(request):
        return
    supplied = request.query_params.get("session_token") or request.headers.get("X-Session-Token", "")
    expected = session.metadata.get("customer_token", "")
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


class DirectHandoffBody(BaseModel):
    session_id: Optional[str] = None
    customer_id: str
    channel: str = "web"
    reason: str = "direct_request"


@router.post("/handoff/direct")
async def direct_handoff(body: DirectHandoffBody, _: None = Depends(verify_api_key)):
    session = await get_or_create_session(
        session_id=body.session_id,
        customer_id=body.customer_id,
        channel=body.channel,
    )
    session.status = SessionStatus.pending_handoff
    session.metadata["handoff_reason"] = body.reason
    session_token = get_customer_token(session)
    await save_session(session)
    await log_session_outcome(
        session_id=session.session_id,
        status="pending_handoff",
        handoff_reason=body.reason,
    )
    return {
        "ok": True,
        "session_id": session.session_id,
        "session_token": session_token,
        "escalated": True,
    }


@router.post("/handoff/{session_id}")
async def escalate_to_human(
    session_id: str, request: Request
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    verify_handoff_access(request, session)
    session.status = SessionStatus.pending_handoff
    session.metadata["handoff_reason"] = "bad_feedback"
    await save_session(session)
    await log_session_outcome(
        session_id=session_id,
        status="pending_handoff",
        handoff_reason=session.metadata.get("handoff_reason", "manual"),
    )
    return {"message": "Escalated to human queue", "session_id": session_id}


@router.post("/handoff/{session_id}/accept")
async def accept_handoff(
    session_id: str,
    agent_id: str = "agent-1",
    _: None = Depends(verify_api_key),
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.human_active
    now = datetime.now(timezone.utc)
    session.metadata["accepted_at"] = now.isoformat()
    session.metadata["assigned_agent"] = agent_id
    await save_session(session)
    await log_session_outcome(
        session_id=session_id,
        status="accepted",
        resolved_by=agent_id,
        handoff_reason=session.metadata.get("handoff_reason", ""),
        accepted_at=now,
        time_to_accept_seconds=max(0, (now - datetime.fromisoformat(session.created_at)).total_seconds()),
    )
    return {
        "message": "Session accepted by human agent",
        "session_id": session_id,
        "agent_id": agent_id,
    }


@router.post("/handoff/{session_id}/resolve")
async def resolve_session(
    session_id: str, _: None = Depends(verify_api_key)
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.resolved
    await save_session(session)
    return {"message": "Session resolved", "session_id": session_id}
