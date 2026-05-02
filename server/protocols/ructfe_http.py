import logging

import httpx

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

TIMEOUT = 5

# Substring matching against the response msg field.
# Source: C4T-BuT-S4D/S4DFarm ructf_http.py
RESPONSES: dict[str, list[str]] = {
    "error": [
        "timeout",
        "game not started",
        "try again later",
        "game over",
        "is not up",
        "no such flag",
    ],
    "accepted": ["accepted", "congrat"],
    "rejected": [
        "bad",
        "wrong",
        "expired",
        "unknown",
        "your own",
        "too old",
        "not in database",
        "already submitted",
        "invalid flag",
    ],
}


def _parse_msg(msg: str) -> str:
    lo = msg.lower()
    for status, substrings in RESPONSES.items():
        if any(s in lo for s in substrings):
            return status
    return "error"


class RuCTFEHTTPProtocol(BaseProtocol):
    name = "ructfe_http"
    display_name = "RuCTFE (HTTP)"
    params_schema = {
        "url": {
            "type": "string",
            "label": "Submission URL",
            "placeholder": "http://monitor.ructfe.org/flags",
        },
        "team_token": {"type": "string", "label": "Team Token", "required": False},
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        url: str = self.params["url"]
        team_token: str = self.params.get("team_token", "")

        # RuCTF uses PUT with X-Team-Token, not POST with Authorization: Bearer.
        headers: dict[str, str] = {}
        if team_token:
            headers["X-Team-Token"] = team_token

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.put(url, json=flags, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.error("RuCTFE HTTP submit failed: %s", exc)
            return [(f, "error", str(exc)) for f in flags]

        if not isinstance(data, list):
            log.warning("RuCTFE HTTP unexpected response: %r", data)
            return [(f, "error", "unexpected response") for f in flags]

        by_flag = {
            item["flag"]: item
            for item in data
            if isinstance(item, dict) and "flag" in item
        }

        results: list[tuple[str, str, str]] = []
        for i, flag in enumerate(flags):
            item = by_flag.get(flag) or (
                data[i] if i < len(data) and isinstance(data[i], dict) else {}
            )
            msg = str(item.get("msg") or "").strip()
            # Strip the "[flag] " prefix the checksystem prepends to some messages.
            msg = msg.replace(f"[{flag}] ", "")
            if not msg:
                msg = "no response"
                log.warning(
                    "RuCTFE HTTP unknown response for flag %s...; treating as error",
                    flag[:8],
                )
            results.append((flag, _parse_msg(msg), msg))
        return results
