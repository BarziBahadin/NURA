import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from core.handoff_controller import (
    HANDOFF_MESSAGE_AR,
    check_handoff_triggers,
    trigger_handoff,
)
from core.logger import log_conversation
from core.orchestrator import generate_response
from core.session_manager import append_turn, get_or_create_session, save_session
from models.message import IncomingMessage
from models.response import NURAResponse
from models.session import SessionStatus

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def verify_api_key(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/message", response_model=NURAResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    payload: IncomingMessage,
    _: None = Depends(verify_api_key),
):
    clean_message = payload.message.strip()[:2000]

    session = await get_or_create_session(
        session_id=payload.session_id,
        customer_id=payload.customer_id,
        channel=payload.channel.value,
    )

    # Already handed off to human
    if session.status in (SessionStatus.pending_handoff, SessionStatus.human_active):
        return NURAResponse(
            session_id=session.session_id,
            response=HANDOFF_MESSAGE_AR,
            channel=session.channel,
            escalated=True,
            confidence=1.0,
        )

    # Generate AI response
    response_text, confidence = await generate_response(session, clean_message)

    # Check handoff
    should_escalate = check_handoff_triggers(session, clean_message, confidence)
    if should_escalate:
        session = trigger_handoff(session)
        response_text = HANDOFF_MESSAGE_AR

    # Save conversation
    await append_turn(session, "customer", clean_message)
    await append_turn(session, "agent", response_text, confidence)
    await save_session(session)

    # Log to DB
    await log_conversation(
        session_id=session.session_id,
        customer_id=payload.customer_id,
        channel=payload.channel.value,
        customer_message=clean_message,
        agent_response=response_text,
        confidence=confidence,
        escalated=should_escalate,
    )

    return NURAResponse(
        session_id=session.session_id,
        response=response_text,
        channel=session.channel,
        escalated=should_escalate,
        confidence=confidence,
    )
