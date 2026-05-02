import logging
from enum import IntEnum

import httpx

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

TIMEOUT = 10


class ChecksystemResult(IntEnum):
    """VolgaCTF HTTP API result codes.

    The /submit endpoint returns these enum member *names* as plain text, e.g. "SUCCESS".
    Source: C4T-BuT-S4D/S4DFarm volgactf.py
    """

    SUCCESS = 0
    ERROR_UNKNOWN = 1
    ERROR_ACCESS_DENIED = 2
    ERROR_COMPETITION_NOT_STARTED = 3
    ERROR_COMPETITION_PAUSED = 4
    ERROR_COMPETITION_FINISHED = 5
    ERROR_FLAG_INVALID = 6
    ERROR_RATELIMIT = 7
    ERROR_FLAG_EXPIRED = 8
    ERROR_FLAG_YOUR_OWN = 9
    ERROR_FLAG_SUBMITTED = 10
    ERROR_FLAG_NOT_FOUND = 11
    ERROR_SERVICE_STATE_INVALID = 12


# Maps each result code to (canonical_status, human_message).
_RESULT_MAP: dict[ChecksystemResult, tuple[str, str]] = {
    ChecksystemResult.SUCCESS: ("accepted", "accepted"),
    ChecksystemResult.ERROR_FLAG_INVALID: ("rejected", "invalid flag"),
    ChecksystemResult.ERROR_FLAG_EXPIRED: ("expired", "flag expired"),
    ChecksystemResult.ERROR_FLAG_YOUR_OWN: ("rejected", "own flag"),
    ChecksystemResult.ERROR_FLAG_SUBMITTED: ("duplicate", "already submitted"),
    ChecksystemResult.ERROR_FLAG_NOT_FOUND: ("rejected", "flag not found"),
    ChecksystemResult.ERROR_COMPETITION_FINISHED: ("rejected", "competition finished"),
    ChecksystemResult.ERROR_UNKNOWN: ("error", "unknown error"),
    ChecksystemResult.ERROR_ACCESS_DENIED: ("error", "access denied"),
    ChecksystemResult.ERROR_COMPETITION_NOT_STARTED: (
        "error",
        "competition not started",
    ),
    ChecksystemResult.ERROR_COMPETITION_PAUSED: ("error", "competition paused"),
    ChecksystemResult.ERROR_RATELIMIT: ("error", "ratelimit"),
    ChecksystemResult.ERROR_SERVICE_STATE_INVALID: ("error", "service down"),
}


class VolgaCTFProtocol(BaseProtocol):
    name = "volgactf"
    display_name = "VolgaCTF"
    params_schema = {
        "host": {
            "type": "string",
            "label": "Host",
            "placeholder": "monitor.volgactf.ru",
        },
        "version": {"type": "string", "label": "API Version", "default": "v1"},
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        host: str = self.params["host"]
        version: str = self.params.get("version", "v1")
        submit_url = f"https://{host}/api/flag/{version}/submit"
        # VolgaCTF authenticates by the attacking team's IP; no auth header needed.
        headers = {"Content-Type": "text/plain"}

        results: list[tuple[str, str, str]] = []
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for flag in flags:
                try:
                    resp = await client.post(
                        submit_url, content=flag.encode(), headers=headers
                    )
                    text = resp.text.strip()

                    # API returns the enum member name as plain text, e.g. "SUCCESS".
                    try:
                        code = ChecksystemResult[text]
                    except KeyError:
                        # Fall back to integer value if the API returns a number.
                        try:
                            code = ChecksystemResult(int(text))
                        except (ValueError, KeyError):
                            log.warning("VolgaCTF unknown response: %r", text)
                            results.append((flag, "error", f"unknown: {text}"))
                            continue

                    canonical, msg = _RESULT_MAP.get(code, ("error", code.name))
                    results.append((flag, canonical, msg))

                except Exception as exc:
                    log.error("VolgaCTF submit error: %s", exc)
                    results.append((flag, "error", str(exc)))

        return results
