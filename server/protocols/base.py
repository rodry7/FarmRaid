from abc import ABC, abstractmethod
from typing import Any


class BaseProtocol(ABC):
    name: str
    display_name: str
    params_schema: dict[str, Any]

    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params

    @abstractmethod
    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        """Submit flags to the competition system.

        Returns a list of (flag, status, response_message).
        status ∈ {accepted, rejected, duplicate, expired, error}
        """

    @staticmethod
    def parse_verdict(text: str) -> str:
        """Map a free-form server response string to a canonical status."""
        lo = text.lower()
        if any(k in lo for k in ("accept", "correct", " ok", "ok\n", "^ok$")):
            return "accepted"
        if any(k in lo for k in ("duplicat", "already", "resubmit", "repeat")):
            return "duplicate"
        if any(k in lo for k in ("expir", "too old", "old flag", "timeout")):
            return "expired"
        if any(k in lo for k in ("invalid", "wrong", "denied", "reject", "bad flag", "not found")):
            return "rejected"
        # "ok" alone is a common accepted signal
        if lo.strip() == "ok":
            return "accepted"
        return "error"
