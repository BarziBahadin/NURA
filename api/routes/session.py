from fastapi import APIRouter, Depends, HTTPException, Request

from config import settings
from core.session_manager import get_pending_handoff_sessions, get_session, save_session
from models.session import SessionStatus

router = APIRouter()


def verify_api_key(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != settings.api_key:
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
    return {"message": "Session closed", "session_id": session_id}


@router.get("/queue")
async def get_queue(_: None = Depends(verify_api_key)):
    sessions = await get_pending_handoff_sessions()
    return {"pending": len(sessions), "sessions": [s.model_dump() for s in sessions]}
