from dataclasses import dataclass

from core.handoff_controller import HANDOFF_MESSAGE_AR, check_handoff_triggers, trigger_handoff
from core.job_queue import JOB_ESCALATION_WEBHOOK, JOB_INTENT_CLASSIFICATION, enqueue_job
from core.logger import log_conversation, log_session_outcome
from core.orchestrator import generate_response
from core.session_manager import append_turn, get_customer_token, get_or_create_session, save_session
from models.session import Session, SessionStatus


@dataclass
class MessagePipelineResult:
    session: Session
    session_token: str | None
    response_text: str
    confidence: float
    source: str | None
    source_doc: str | None
    escalated: bool


async def process_customer_message(
    session_id: str | None,
    customer_id: str,
    channel: str,
    message: str,
    include_session_token: bool = True,
    attachment_url: str | None = None,
    message_type: str = "text",
) -> MessagePipelineResult:
    clean_message = message.strip()[:2000]
    session = await get_or_create_session(session_id=session_id, customer_id=customer_id, channel=channel)

    if session.status in (SessionStatus.pending_handoff, SessionStatus.human_active):
        token = get_customer_token(session) if include_session_token else None
        await append_turn(session, "customer", clean_message, source="customer",
                          attachment_url=attachment_url, message_type=message_type)
        return MessagePipelineResult(session, token, "", 1.0, None, None, True)

    response_text, confidence, source, source_doc = await generate_response(session, clean_message)

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
            customer_id=customer_id,
            channel=channel,
            trigger_message=clean_message,
        )

    token = get_customer_token(session) if include_session_token else None
    await append_turn(session, "customer", clean_message, source="customer",
                      attachment_url=attachment_url, message_type=message_type)
    await append_turn(session, "agent", response_text, confidence)
    await save_session(session)

    logged_source = source if not should_escalate else "escalated"
    await log_conversation(
        session_id=session.session_id,
        customer_id=customer_id,
        channel=channel,
        customer_message=clean_message,
        agent_response=response_text,
        confidence=confidence,
        escalated=should_escalate,
        source=logged_source,
    )
    await enqueue_job(
        JOB_INTENT_CLASSIFICATION,
        session_id=session.session_id,
        customer_id=customer_id,
        channel=channel,
        message_text=clean_message,
        confidence=confidence,
        source=logged_source,
        escalated=should_escalate,
    )

    return MessagePipelineResult(
        session=session,
        session_token=token,
        response_text=response_text,
        confidence=confidence,
        source=None if should_escalate else source,
        source_doc=None if should_escalate else source_doc,
        escalated=should_escalate,
    )
