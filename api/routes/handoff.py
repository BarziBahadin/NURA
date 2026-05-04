import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import verify_api_key, verify_session_access
from core.logger import log_session_outcome
from core.session_manager import get_customer_token, get_or_create_session, get_session, save_session
from core.utils import fire_task
from models.session import SessionStatus
from routes.cases import ensure_case_for_session
from routes import cases as case_routes
from datetime import datetime, timezone

AGENT_JOINED_AR = "✅ تم التواصل مع أحد أعضاء الفريق. يمكنك الآن الكتابة مباشرة."

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _telegram_chat_id(session, session_id: str) -> int | None:
    if session.channel != "telegram":
        return None
    try:
        return int(session.customer_id or session_id[3:])
    except Exception:
        return None

class DirectHandoffBody(BaseModel):
    session_id: Optional[str] = None
    customer_id: str = Field(..., max_length=128)
    channel: str = Field(default="web", max_length=32)
    reason: str = Field(default="direct_request", max_length=128)


def case_defaults_for_handoff(reason: str) -> tuple[str, str]:
    reason_lower = (reason or "").lower()
    dept = "general"
    priority = "normal"
    if "feedback" in reason_lower or "complaint" in reason_lower:
        dept, priority = "complaints", "high"
    elif "billing" in reason_lower or "payment" in reason_lower:
        dept, priority = "billing", "normal"
    elif "technical" in reason_lower or "internet" in reason_lower or "network" in reason_lower:
        dept, priority = "technical", "normal"
    if not case_routes.is_valid_department_code(dept):
        dept = "general"
    return dept, priority


@router.post("/handoff/direct")
@limiter.limit("20/minute")
async def direct_handoff(body: DirectHandoffBody, request: Request):
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
    department, priority = case_defaults_for_handoff(body.reason)
    case = await ensure_case_for_session(
        session,
        reason=body.reason,
        department=department,
        priority=priority,
        actor="system",
    )
    return {
        "ok": True,
        "session_id": session.session_id,
        "session_token": session_token,
        "escalated": True,
        "case_number": case.get("case_number") if case else None,
    }


@router.post("/handoff/{session_id}")
async def escalate_to_human(
    session_id: str, request: Request
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await verify_session_access(request, session)
    session.status = SessionStatus.pending_handoff
    session.metadata["handoff_reason"] = "bad_feedback"
    await save_session(session)
    await log_session_outcome(
        session_id=session_id,
        status="pending_handoff",
        handoff_reason=session.metadata.get("handoff_reason", "manual"),
    )
    reason = session.metadata.get("handoff_reason", "manual")
    department, priority = case_defaults_for_handoff(reason)
    case = await ensure_case_for_session(
        session,
        reason=reason,
        department=department,
        priority=priority,
        actor="system",
    )
    return {
        "message": "Escalated to human queue",
        "session_id": session_id,
        "case_number": case.get("case_number") if case else None,
    }


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
    chat_id = _telegram_chat_id(session, session_id)
    if chat_id is not None:
        try:
            from routes.telegram import _send
            fire_task(_send(chat_id, AGENT_JOINED_AR), label="tg:agent_joined")
        except Exception:
            pass
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
    chat_id = _telegram_chat_id(session, session_id)
    if chat_id is not None:
        try:
            from routes.telegram import send_resolved_to_telegram
            fire_task(send_resolved_to_telegram(chat_id), label="tg:resolved")
        except Exception:
            pass
    return {"message": "Session resolved", "session_id": session_id}
