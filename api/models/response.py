from typing import Optional

from pydantic import BaseModel


class NURAResponse(BaseModel):
    session_id: str
    session_token: Optional[str] = None
    response: str
    channel: str
    escalated: bool = False
    agent_id: Optional[str] = None
    confidence: float = 0.0
    source: Optional[str] = None        # "rules" | "local_model" | "openai"
    source_doc: Optional[str] = None    # filename that answered this query (RAG only)
    status: str = "ok"
