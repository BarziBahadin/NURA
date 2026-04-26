from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Channel(str, Enum):
    web = "web"
    whatsapp = "whatsapp"
    telegram = "telegram"
    email = "email"
    messenger = "messenger"
    teams = "teams"


class IncomingMessage(BaseModel):
    session_id: Optional[str] = None
    channel: Channel = Channel.web
    customer_id: str
    message: str = Field(..., max_length=2000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StandardMessage(BaseModel):
    session_id: Optional[str]
    channel: str
    customer_id: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
