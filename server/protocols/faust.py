import asyncio
import logging

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 5
APPEND_TIMEOUT = 0.05
BUFSIZE = 4096

# Source: C4T-BuT-S4D/S4DFarm faust.py
RESPONSES: dict[str, list[str]] = {
    "error":    ["ERR", "INV"],
    "accepted": ["OK"],
    "rejected": ["DUP", "OWN", "OLD"],
}


async def _recvall(reader: asyncio.StreamReader) -> bytes:
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


def _parse_response(line: str) -> str:
    for status, codes in RESPONSES.items():
        if any(c in line for c in codes):
            return status
    return "error"


class FAUSTProtocol(BaseProtocol):
    name = "faust"
    display_name = "FAUST CTF (TCP)"
    params_schema = {
        "host": {"type": "string",  "label": "Host", "placeholder": "10.10.10.10"},
        "port": {"type": "integer", "label": "Port", "default": 31337},
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        host: str = self.params["host"]
        port: int = int(self.params.get("port", 31337))

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT
            )
        except Exception as exc:
            log.error("FAUST TCP connect %s:%s failed: %s", host, port, exc)
            return [(f, "error", "connection failed") for f in flags]

        results: list[tuple[str, str, str]] = []
        try:
            greeting = await _recvall(reader)
            if b"One flag per line please" not in greeting:
                log.warning("FAUST TCP unexpected greeting: %s", greeting[:200])

            # Send all flags at once, one per line.
            writer.write(b"\n".join(f.encode() for f in flags) + b"\n")
            await writer.drain()

            # Read responses in batches; consume flags in order.
            remaining = list(flags)
            while remaining:
                raw = await _recvall(reader)
                if not raw:
                    break
                for line in raw.decode(errors="replace").strip().splitlines():
                    if not remaining:
                        break
                    flag = remaining.pop(0)
                    # Strip "FLAG " prefix the server prepends to each response line.
                    line = line.replace(f"{flag} ", "")
                    results.append((flag, _parse_response(line), line))

            for flag in remaining:
                results.append((flag, "error", "no response"))

        except Exception as exc:
            log.error("FAUST TCP submit error: %s", exc)
            seen = {r[0] for r in results}
            for flag in flags:
                if flag not in seen:
                    results.append((flag, "error", str(exc)))
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass

        return results
