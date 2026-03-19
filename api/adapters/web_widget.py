from adapters.base import BaseAdapter
from models.message import StandardMessage
from models.response import NURAResponse


class WebWidgetAdapter(BaseAdapter):
    def parse_incoming(self, raw_payload: dict) -> StandardMessage:
        return StandardMessage(
            session_id=raw_payload.get("session_id"),
            channel="web",
            customer_id=raw_payload.get("customer_id", "anonymous"),
            message=raw_payload.get("message", ""),
            metadata=raw_payload.get("metadata", {}),
        )

    def format_outgoing(self, response: NURAResponse) -> dict:
        return {
            "session_id": response.session_id,
            "response": response.response,
            "escalated": response.escalated,
            "confidence": response.confidence,
        }
