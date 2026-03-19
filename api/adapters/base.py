from abc import ABC, abstractmethod

from models.message import StandardMessage
from models.response import NURAResponse


class BaseAdapter(ABC):
    @abstractmethod
    def parse_incoming(self, raw_payload: dict) -> StandardMessage:
        pass

    @abstractmethod
    def format_outgoing(self, response: NURAResponse) -> dict:
        pass

    def verify_webhook(self, request) -> bool:
        return True
