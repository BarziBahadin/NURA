from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import verify_api_key
from core.session_manager import get_all_sessions, get_pending_handoff_sessions, get_session, save_session
from models.session import SessionStatus

router = APIRouter()


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
    return {"message": "Session closed", "session_id": session_id}


@router.post("/session/{session_id}/resolve")
async def resolve_session(session_id: str, _: None = Depends(verify_api_key)):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.resolved
    await save_session(session)
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
    sessions = await get_pending_handoff_sessions()
    return {"pending": len(sessions), "sessions": [s.model_dump() for s in sessions]}
