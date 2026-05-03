from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    active = "ACTIVE"
    pending_handoff = "PENDING_HANDOFF"
    human_active = "HUMAN_ACTIVE"
    resolved = "RESOLVED"


class ConversationTurn(BaseModel):
    role: str
    message: str
    timestamp: str
    confidence: Optional[float] = None
    source: str = "bot"
    attachment_url: Optional[str] = None
    message_type: str = "text"


class Session(BaseModel):
    session_id: str
    customer_id: str
    channel: str
    status: SessionStatus = SessionStatus.active
    history: List[ConversationTurn] = Field(default_factory=list)
    failure_count: int = 0
    negative_score: int = 0
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
