import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.handoff_controller import (
    HANDOFF_MESSAGE_AR,
    check_handoff_triggers,
    trigger_handoff,
)
from core.job_queue import JOB_ESCALATION_WEBHOOK, JOB_INTENT_CLASSIFICATION, enqueue_job
from core.logger import log_conversation, log_session_outcome
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
    response_text, confidence, source, source_doc = await generate_response(session, clean_message)

    # Check handoff
    should_escalate, handoff_reason = check_handoff_triggers(session, clean_message, confidence)
    if should_escalate:
        session = trigger_handoff(session)
        session.metadata["handoff_reason"] = handoff_reason
        response_text = HANDOFF_MESSAGE_AR
        await log_session_outcome(
            session_id=session.session_id,
            status="pending_handoff",
            handoff_reason=handoff_reason,
        )
        await enqueue_job(
            JOB_ESCALATION_WEBHOOK,
            session_id=session.session_id,
            customer_id=payload.customer_id,
            channel=payload.channel.value,
            trigger_message=clean_message,
        )

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
    await enqueue_job(
        JOB_INTENT_CLASSIFICATION,
        session_id=session.session_id,
        customer_id=payload.customer_id,
        channel=payload.channel.value,
        message_text=clean_message,
        confidence=confidence,
        source=source if not should_escalate else "escalated",
        escalated=should_escalate,
    )

    return NURAResponse(
        session_id=session.session_id,
        session_token=session_token,
        response=response_text,
        channel=session.channel,
        escalated=should_escalate,
        confidence=confidence,
        source=None if should_escalate else source,
        source_doc=None if should_escalate else source_doc,
    )
