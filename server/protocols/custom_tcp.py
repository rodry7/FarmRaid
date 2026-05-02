import asyncio
import logging
import re

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 5
BUFSIZE = 4096


async def _readline(reader: asyncio.StreamReader, timeout: float) -> str:
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        return line.decode(errors="replace").rstrip("\r\n")
    except asyncio.TimeoutError:
        return ""


class CustomTCPProtocol(BaseProtocol):
    name = "custom_tcp"
    display_name = "Custom TCP"
    params_schema = {
        "host": {"type": "string", "label": "Host", "placeholder": "10.10.10.10"},
        "port": {"type": "integer", "label": "Port", "default": 31337},
        "team_token": {
            "type": "string",
            "label": "Team Token",
            "required": False,
            "description": "Optional. Sent immediately on connect, or after the handshake line if set.",
        },
        "token_line": {
            "type": "string",
            "label": "Handshake Line",
            "required": False,
            "placeholder": "Enter your token:",
            "description": "Substring to wait for before sending the team token (handshake detection).",
        },
        "flag_regex": {
            "type": "string",
            "label": "Response Regex",
            "required": False,
            "placeholder": "accepted|ok",
            "description": "Matched against each per-flag response line. Blank = built-in verdict parsing.",
        },
        "timeout": {"type": "integer", "label": "Timeout (s)", "default": 10},
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        host: str = self.params["host"]
        port: int = int(self.params.get("port", 31337))
        team_token: str = (self.params.get("team_token") or "").strip()
        token_line: str = (self.params.get("token_line") or "").strip()
        flag_regex: str = (self.params.get("flag_regex") or "").strip()
        connect_timeout: int = int(self.params.get("timeout", CONNECT_TIMEOUT))

        compiled_re: re.Pattern | None = None
        if flag_regex:
            try:
                compiled_re = re.compile(flag_regex, re.IGNORECASE)
            except re.error as exc:
                log.warning("custom_tcp: invalid flag_regex %r: %s", flag_regex, exc)

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=connect_timeout
            )
        except Exception as exc:
            log.error("Custom TCP connect %s:%s failed: %s", host, port, exc)
            return [(f, "error", "connection failed") for f in flags]

        results: list[tuple[str, str, str]] = []
        try:
            if team_token:
                if token_line:
                    # Wait for the handshake prompt, then send the token.
                    deadline = asyncio.get_event_loop().time() + connect_timeout
                    while True:
                        remaining = deadline - asyncio.get_event_loop().time()
                        if remaining <= 0:
                            log.warning(
                                "custom_tcp: timed out waiting for %r", token_line
                            )
                            break
                        line = await _readline(reader, min(remaining, READ_TIMEOUT))
                        if not line or token_line in line:
                            break
                else:
                    # No handshake — drain any greeting, then send token immediately.
                    try:
                        await asyncio.wait_for(reader.read(BUFSIZE), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass

                writer.write(team_token.encode() + b"\n")
                await writer.drain()
                # Consume the server's acknowledgement line.
                try:
                    await asyncio.wait_for(reader.readline(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass
            else:
                # Drain any greeting so subsequent reads return flag responses.
                try:
                    await asyncio.wait_for(reader.read(BUFSIZE), timeout=1.0)
                except asyncio.TimeoutError:
                    pass

            for flag in flags:
                writer.write(flag.encode() + b"\n")
                await writer.drain()

                response = await _readline(reader, READ_TIMEOUT)
                response = response.replace(f"[{flag}] ", "").strip()
                results.append((flag, self._classify(response, compiled_re), response))

        except Exception as exc:
            log.error("Custom TCP submit error: %s", exc)
            while len(results) < len(flags):
                results.append((flags[len(results)], "error", str(exc)))
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass

        return results

    def _classify(self, line: str, compiled_re: re.Pattern | None) -> str:
        if compiled_re:
            return "accepted" if compiled_re.search(line) else "rejected"
        return self.parse_verdict(line)
