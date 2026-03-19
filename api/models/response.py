from typing import Optional

from pydantic import BaseModel


class NURAResponse(BaseModel):
    session_id: str
    response: str
    channel: str
    escalated: bool = False
    agent_id: Optional[str] = None
    confidence: float = 0.0
    status: str = "ok"
