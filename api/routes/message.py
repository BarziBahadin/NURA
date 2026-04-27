import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.handoff_controller import (
    HANDOFF_MESSAGE_AR,
    check_handoff_triggers,
    trigger_handoff,
)
from core.logger import log_conversation
from core.orchestrator import generate_response
from core.session_manager import append_turn, get_customer_token, get_or_create_session, save_session
from models.message import IncomingMessage
from models.response import NURAResponse
from models.session import SessionStatus

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/message", response_model=NURAResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    payload: IncomingMessage,
):
    clean_message = payload.message.strip()[:2000]

    session = await get_or_create_session(
        session_id=payload.session_id,
        customer_id=payload.customer_id,
        channel=payload.channel.value,
    )

    # Already handed off to human — save customer message so admin sees it, return no bot reply
    if session.status in (SessionStatus.pending_handoff, SessionStatus.human_active):
        token = get_customer_token(session)
        await save_session(session)
        await append_turn(session, "customer", clean_message, source="customer")
        return NURAResponse(
            session_id=session.session_id,
            session_token=token,
            response="",
            channel=session.channel,
            escalated=True,
            confidence=1.0,
        )

    # Generate AI response
    response_text, confidence, source = await generate_response(session, clean_message)

    # Check handoff
    should_escalate = check_handoff_triggers(session, clean_message, confidence)
    if should_escalate:
        session = trigger_handoff(session)
        response_text = HANDOFF_MESSAGE_AR

    session_token = get_customer_token(session)

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
        source=source if not should_escalate else "escalated",
    )

    return NURAResponse(
        session_id=session.session_id,
        session_token=session_token,
        response=response_text,
        channel=session.channel,
        escalated=should_escalate,
        confidence=confidence,
        source=None if should_escalate else source,
    )
