import logging

import httpx

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

TIMEOUT = 30


class ForcadHTTPProtocol(BaseProtocol):
    name = "forcad_http"
    display_name = "ForcAD (HTTP)"
    params_schema = {
        "url": {
            "type": "string",
            "label": "Submission URL",
            "placeholder": "http://10.10.10.10:8080/flags",
        },
        "team_token": {"type": "string", "label": "Team Token", "required": False},
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        url: str = self.params["url"]
        team_token: str = self.params.get("team_token", "")

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if team_token:
            headers["Authorization"] = f"Bearer {team_token}"

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.put(url, json=flags, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.error("ForcAD HTTP submit failed: %s", exc)
            return [(f, "error", str(exc)) for f in flags]

        # ForcAD response: list of {"flag": "...", "verdict": "...", "msg": "..."}
        # Build flag → result mapping; fall back to positional if needed.
        if isinstance(data, list):
            by_flag: dict[str, dict] = {}
            positional: list[dict] = []
            for item in data:
                if isinstance(item, dict):
                    if "flag" in item:
                        by_flag[item["flag"]] = item
                    positional.append(item)

            results: list[tuple[str, str, str]] = []
            for i, flag in enumerate(flags):
                item = by_flag.get(flag) or (
                    positional[i] if i < len(positional) else {}
                )
                verdict_raw = (
                    item.get("verdict") or item.get("msg") or item.get("status") or ""
                )
                msg = str(verdict_raw)
                results.append((flag, self.parse_verdict(msg), msg))
            return results

        log.warning("ForcAD HTTP unexpected response format: %r", data)
        return [(f, "error", "unexpected response") for f in flags]
