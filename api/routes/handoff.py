from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import verify_api_key
from core.session_manager import get_session, save_session
from models.session import SessionStatus

router = APIRouter()


@router.post("/handoff/{session_id}")
async def escalate_to_human(
    session_id: str, _: None = Depends(verify_api_key)
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.pending_handoff
    await save_session(session)
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
    session.metadata["assigned_agent"] = agent_id
    await save_session(session)
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
