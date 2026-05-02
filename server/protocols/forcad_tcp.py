import asyncio
import logging

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 5
APPEND_TIMEOUT = 0.05
BUFSIZE = 4096

# Verdict substring matching per ctfcup/ForcAD TCP checksystem conventions.
# Source: C4T-BuT-S4D/S4DFarm ctfcup_tcp.py
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
        "self",
        "invalid",
        "already_submitted",
        "team_not_found",
        "too_old",
    ],
}


async def _recvall(reader: asyncio.StreamReader) -> bytes:
    """Two-phase read: initial READ_TIMEOUT then drain with short APPEND_TIMEOUT."""
    chunks: list[bytes] = []
    try:
        chunk = await asyncio.wait_for(reader.read(BUFSIZE), timeout=READ_TIMEOUT)
        if chunk:
            chunks.append(chunk)
    except asyncio.TimeoutError:
        return b""

    while True:
        try:
            chunk = await asyncio.wait_for(reader.read(BUFSIZE), timeout=APPEND_TIMEOUT)
            if not chunk:
                break
            chunks.append(chunk)
        except asyncio.TimeoutError:
            break

    return b"".join(chunks)


def _parse_response(msg: str) -> str:
    lo = msg.lower()
    for status, substrings in RESPONSES.items():
        if any(s in lo for s in substrings):
            return status
    return "error"


class ForcadTCPProtocol(BaseProtocol):
    name = "forcad_tcp"
    display_name = "ForcAD / RuCTFE (TCP)"
    params_schema = {
        "host": {"type": "string", "label": "Host", "placeholder": "10.10.10.10"},
        "port": {"type": "integer", "label": "Port", "default": 31337},
        "team_token": {"type": "string", "label": "Team Token", "required": False},
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        host: str = self.params["host"]
        port: int = int(self.params.get("port", 31337))
        team_token: str = self.params.get("team_token", "")

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT
            )
        except Exception as exc:
            log.error("ForcAD TCP connect %s:%s failed: %s", host, port, exc)
            return [(f, "error", "connection failed") for f in flags]

        results: list[tuple[str, str, str]] = []
        try:
            # Read server greeting (e.g. "Please enter flags").
            greeting = await _recvall(reader)
            log.debug("ForcAD TCP greeting from %s:%s: %s", host, port, greeting[:200])

            # ForcAD proper requires a team token; ctfcup/ructf use IP-based auth.
            if team_token:
                writer.write(team_token.encode() + b"\n")
                await writer.drain()
                # Consume acknowledgement.
                try:
                    await asyncio.wait_for(reader.read(BUFSIZE), timeout=2)
                except asyncio.TimeoutError:
                    pass

            # Send flags one at a time, reading one response per flag.
            for flag in flags:
                writer.write(flag.encode() + b"\n")
                await writer.drain()

                raw = await _recvall(reader)
                msg = raw.decode(errors="replace").strip()
                # Take only the first line of a multi-line response.
                if msg:
                    msg = msg.splitlines()[0]
                # Strip the "[flag] " prefix some backends prepend to responses.
                msg = msg.replace(f"[{flag}] ", "")

                results.append((flag, _parse_response(msg), msg))

        except Exception as exc:
            log.error("ForcAD TCP submit error: %s", exc)
            while len(results) < len(flags):
                results.append((flags[len(results)], "error", str(exc)))
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass

        return results
