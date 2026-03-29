import logging

from config import settings
from core.sentiment import analyze_sentiment
from models.session import Session, SessionStatus

logger = logging.getLogger(__name__)

HANDOFF_MESSAGE_AR = (
    "شكرًا لصبرك. سأقوم بتحويلك الآن إلى أحد أعضاء فريق الدعم. "
    "يرجى الانتظار لحظة وسيتواصل معك أحد الموظفين قريبًا."
)


def check_handoff_triggers(
    session: Session, message: str, confidence: float
) -> bool:
    if not settings.handoff_enabled:
        return False

    triggers = settings.handoff_triggers_list
    sentiment = analyze_sentiment(message)

    session.negative_score += sentiment["negative_score"]

    if "explicit_request" in triggers and sentiment["escalation_requested"]:
        logger.info(f"Handoff triggered: explicit request — session {session.session_id}")
        return True

    if "angry_sentiment" in triggers and session.negative_score >= 2:
        logger.info(f"Handoff triggered: angry sentiment — session {session.session_id}")
        return True

    if "two_failures" in triggers and session.failure_count >= 2:
        logger.info(f"Handoff triggered: two failures — session {session.session_id}")
        return True

    if confidence < 0.05:
        session.failure_count += 1
        logger.info(
            f"Low confidence ({confidence}) — failure count: {session.failure_count}"
        )

    return False


def trigger_handoff(session: Session) -> Session:
    session.status = SessionStatus.pending_handoff
    return session
