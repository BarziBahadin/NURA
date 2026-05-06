import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import verify_session_access
from core.message_pipeline import process_customer_message
from core.session_manager import get_session
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
    session_id = payload.session_id
    if session_id:
        existing = await get_session(session_id)
        if existing and existing.status != SessionStatus.resolved:
            await verify_session_access(request, existing)
        elif not existing:
            session_id = None

    result = await process_customer_message(
        session_id=session_id,
        customer_id=payload.customer_id,
        channel=payload.channel.value,
        message=payload.message,
        include_session_token=True,
        attachment_url=payload.attachment_url,
        message_type=payload.message_type,
    )
    return NURAResponse(
        session_id=result.session.session_id,
        session_token=result.session_token,
        response=result.response_text,
        channel=result.session.channel,
        escalated=result.escalated,
        confidence=result.confidence,
        source=result.source,
        source_doc=result.source_doc,
    )
