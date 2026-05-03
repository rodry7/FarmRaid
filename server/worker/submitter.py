import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from sqlalchemy import func, select, update

from config_manager import get_config
from database import AsyncSessionLocal
from models import Flag
from protocols import get_protocol

log = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Sentinel used by the lifespan to cancel the background task cleanly.
_stop_event: asyncio.Event | None = None


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def _expire_old_flags(db, flag_lifetime: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=flag_lifetime)
    result = await db.execute(
        update(Flag)
        .where(Flag.status.in_(["pending", "queued"]), Flag.captured_at < cutoff)
        .values(status="expired")
        .returning(Flag.id)
    )
    await db.commit()
    rows = result.fetchall()
    return len(rows)


async def _claim_pending(db, limit: int) -> list[Flag]:
    """Atomically mark up to *limit* pending flags as queued and return them."""
    # Subquery selects the IDs we want to claim.
    subq = (
        select(Flag.id)
        .where(Flag.status == "pending")
        .order_by(Flag.captured_at)
        .limit(limit)
        .scalar_subquery()
    )
    result = await db.execute(
        update(Flag).where(Flag.id.in_(subq)).values(status="queued").returning(Flag)
    )
    await db.commit()
    return list(result.scalars().all())


async def _publish_stats(redis: aioredis.Redis) -> None:
    """Publish a stats snapshot to the flag_updates channel."""
    try:
        async with AsyncSessionLocal() as db:
            counts: dict[str, int] = {}
            for s in ("pending", "accepted", "rejected"):
                res = await db.execute(
                    select(func.count()).select_from(Flag).where(Flag.status == s)
                )
                counts[s] = res.scalar_one() or 0
            total_res = await db.execute(select(func.count()).select_from(Flag))
            total = total_res.scalar_one() or 0
        await redis.publish(
            "flag_updates",
            json.dumps(
                {
                    "type": "stats",
                    "data": {
                        "total_flags": total,
                        "accepted": counts["accepted"],
                        "rejected": counts["rejected"],
                        "pending": counts["pending"],
                    },
                }
            ),
        )
    except Exception as exc:
        log.warning("Failed to publish stats: %s", exc)


async def _publish(
    redis: aioredis.Redis,
    flag: Flag,
    status: str,
    response: str,
    submitted_at: datetime,
) -> None:
    try:
        await redis.publish(
            "flag_updates",
            json.dumps(
                {
                    "type": "flag",
                    "data": {
                        "flag": flag.flag,
                        "status": status,
                        "response": response,
                        "team_id": flag.team_id,
                        "exploit_id": flag.exploit_id,
                        "captured_at": flag.captured_at.isoformat(),
                        "submitted_at": submitted_at.isoformat(),
                    },
                }
            ),
        )
    except Exception as exc:
        log.warning("Redis publish failed: %s", exc)


async def _run_cycle(redis: aioredis.Redis) -> None:
    async with AsyncSessionLocal() as db:
        submission_cfg = await get_config(db, "submission") or {}
        competition_cfg = await get_config(db, "competition") or {}

    flag_lifetime: int = int(competition_cfg.get("flag_lifetime", 300))
    protocol_name: str = submission_cfg.get("protocol", "")
    protocol_params: dict = submission_cfg.get("params") or {}
    submit_flag_limit: int = int(submission_cfg.get("submit_flag_limit", 100))

    if not protocol_name:
        log.debug("No protocol configured, skipping submission cycle")
        return

    async with AsyncSessionLocal() as db:
        expired = await _expire_old_flags(db, flag_lifetime)
        if expired:
            log.info("Expired %d stale flags", expired)

    async with AsyncSessionLocal() as db:
        flags = await _claim_pending(db, submit_flag_limit)

    if not flags:
        return

    log.info("Submitting %d flags via %s", len(flags), protocol_name)
    flag_strings = [f.flag for f in flags]
    flag_map: dict[str, Flag] = {f.flag: f for f in flags}

    try:
        protocol = get_protocol(protocol_name, protocol_params)
        results = await asyncio.wait_for(protocol.submit(flag_strings), timeout=60)
    except asyncio.TimeoutError:
        log.error("Protocol submission timed out after 60s — reverting to pending")
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Flag)
                .where(Flag.id.in_([f.id for f in flags]))
                .values(status="pending")
            )
            await db.commit()
        return
    except Exception as exc:
        log.error("Protocol submission failed: %s — reverting to pending", exc)
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Flag)
                .where(Flag.id.in_([f.id for f in flags]))
                .values(status="pending")
            )
            await db.commit()
        return

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        for flag_str, status, response in results:
            flag_obj = flag_map.get(flag_str)
            if flag_obj is None:
                continue
            await db.execute(
                update(Flag)
                .where(Flag.id == flag_obj.id)
                .values(status=status, response=response[:500], submitted_at=now)
            )
            await _publish(redis, flag_obj, status, response, now)
        await db.commit()

    accepted = sum(1 for _, s, _ in results if s == "accepted")
    log.info(
        "Submission cycle complete: %d accepted / %d total",
        accepted,
        len(results),
    )
    await _publish_stats(redis)


async def run_submitter() -> None:
    """Background task: submits pending flags on a configurable interval."""
    redis: aioredis.Redis = await _get_redis()
    log.info("Submitter started (Redis: %s)", REDIS_URL)

    try:
        while True:
            # Re-read submit_period each cycle so UI changes take effect immediately.
            try:
                async with AsyncSessionLocal() as db:
                    submission_cfg = await get_config(db, "submission") or {}
                submit_period: int = int(submission_cfg.get("submit_period", 10))
            except Exception:
                submit_period = 10

            try:
                await _run_cycle(redis)
            except Exception as exc:
                log.error("Submitter cycle error: %s", exc, exc_info=True)

            await asyncio.sleep(submit_period)
    except asyncio.CancelledError:
        log.info("Submitter stopped")
        raise
    finally:
        await redis.aclose()
