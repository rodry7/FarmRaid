import asyncio
import logging
import os

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import func, select

from auth import ALGORITHM, SECRET_KEY
from database import AsyncSessionLocal
from models import Exploit, Flag, Team

log = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
CHANNEL = "flag_updates"


def _valid_token(token: str) -> bool:
    if not token:
        return False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub") == "admin"
    except JWTError:
        return False


async def _snapshot_stats() -> dict:
    """Query current flag counts; used to pre-fill the client on connect."""
    async with AsyncSessionLocal() as db:
        counts: dict[str, int] = {}
        for s in ("pending", "accepted", "rejected"):
            res = await db.execute(
                select(func.count()).select_from(Flag).where(Flag.status == s)
            )
            counts[s] = res.scalar_one() or 0
        total_res = await db.execute(select(func.count()).select_from(Flag))
        total = total_res.scalar_one() or 0
        exploits_res = await db.execute(
            select(func.count()).select_from(Exploit).where(Exploit.enabled.is_(True))
        )
        active_exploits = exploits_res.scalar_one() or 0
        teams_res = await db.execute(
            select(func.count()).select_from(Team).where(Team.active.is_(True))
        )
        active_teams = teams_res.scalar_one() or 0
    return {
        "type": "stats",
        "data": {
            "total_flags": total,
            "accepted": counts["accepted"],
            "rejected": counts["rejected"],
            "pending": counts["pending"],
            "exploits_active": active_exploits,
            "teams_active": active_teams,
        },
    }


@router.websocket("/ws/feed")
async def ws_feed(websocket: WebSocket, token: str = "") -> None:
    await websocket.accept()

    if not _valid_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Send a stats snapshot immediately so the client has numbers before any event.
    try:
        await websocket.send_json(await _snapshot_stats())
    except Exception as exc:
        log.warning("Could not send initial snapshot: %s", exc)

    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(CHANNEL)

        async def forward_redis() -> None:
            """Forward Redis pub/sub messages to the WebSocket; reconnects on Redis error."""
            while True:
                try:
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            try:
                                await websocket.send_text(message["data"])
                            except Exception:
                                # WebSocket gone — stop forwarding.
                                return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log.warning("Redis pubsub error (reconnecting): %s", exc)
                    await asyncio.sleep(1)
                    try:
                        await pubsub.subscribe(CHANNEL)
                    except Exception:
                        await asyncio.sleep(2)

        async def drain_ws() -> None:
            """Consume and discard incoming WebSocket frames.

            Returns when the client disconnects (any exception = disconnect).
            This is the disconnect sentinel for asyncio.wait.
            """
            try:
                while True:
                    await websocket.receive_text()
            except (WebSocketDisconnect, Exception):
                pass

        forward_task = asyncio.create_task(forward_redis())
        drain_task = asyncio.create_task(drain_ws())

        try:
            # Block until either side closes.
            await asyncio.wait(
                [forward_task, drain_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            forward_task.cancel()
            drain_task.cancel()
            await asyncio.gather(forward_task, drain_task, return_exceptions=True)

    finally:
        try:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()
        except Exception:
            pass
        try:
            await redis_client.aclose()
        except Exception:
            pass
