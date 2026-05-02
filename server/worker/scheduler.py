import asyncio
import logging

from sqlalchemy import select

from config_manager import get_config
from database import AsyncSessionLocal
from models import Exploit, Team
from worker.exploit_runner import run_exploit

log = logging.getLogger(__name__)

CONCURRENCY_CAP = 50
DB_POLL_INTERVAL = 5  # seconds between DB state refreshes
TICK_INTERVAL = 1  # seconds between scheduling ticks

# Module-level state — set when run_scheduler() starts.
# trigger_exploit_now() uses these so it shares the same semaphore & task set.
_semaphore: asyncio.Semaphore | None = None
_running_tasks: set[asyncio.Task] = set()


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        # Fallback: create one if trigger_exploit_now() is called before scheduler starts.
        _semaphore = asyncio.Semaphore(CONCURRENCY_CAP)
    return _semaphore


def _fire(exploit: Exploit, team: Team, flag_format: str) -> None:
    """Dispatch a single exploit-vs-team run as a background task."""
    task = asyncio.create_task(
        run_exploit(
            exploit_id=exploit.id,
            exploit_name=exploit.name,
            exploit_filename=exploit.filename,
            exploit_language=exploit.language,
            exploit_timeout=exploit.timeout,
            team_id=team.id,
            team_ip=team.ip,
            flag_format=flag_format,
            semaphore=_get_semaphore(),
        ),
        name=f"exploit-{exploit.id}-team-{team.id}",
    )
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)


async def _load_db_state() -> tuple[list[Exploit], list[Team], str]:
    """Read enabled exploits, active teams, and current flag format from the DB."""
    async with AsyncSessionLocal() as db:
        exploits_res = await db.execute(
            select(Exploit).where(Exploit.enabled.is_(True))
        )
        exploits = list(exploits_res.scalars().all())

        teams_res = await db.execute(select(Team).where(Team.active.is_(True)))
        teams = list(teams_res.scalars().all())

        competition_cfg = await get_config(db, "competition") or {}
        flag_format: str = competition_cfg.get("flag_format", r"[A-Z0-9]{31}=")

    return exploits, teams, flag_format


async def trigger_exploit_now(exploit_id: int) -> int:
    """Immediately run *exploit_id* against all active teams.

    Bypasses the period timer.  Returns the number of teams dispatched to.
    Called by POST /api/exploits/{id}/run.
    """
    async with AsyncSessionLocal() as db:
        exploit_res = await db.execute(select(Exploit).where(Exploit.id == exploit_id))
        exploit = exploit_res.scalar_one_or_none()
        if exploit is None:
            return 0

        teams_res = await db.execute(select(Team).where(Team.active.is_(True)))
        teams = list(teams_res.scalars().all())

        competition_cfg = await get_config(db, "competition") or {}
        flag_format: str = competition_cfg.get("flag_format", r"[A-Z0-9]{31}=")

    for team in teams:
        _fire(exploit, team, flag_format)

    log.info(
        "Manual trigger: exploit %s dispatched against %d team(s)",
        exploit.name,
        len(teams),
    )
    return len(teams)


async def run_scheduler() -> None:
    """Background task: runs each enabled exploit against all active teams on its period."""
    global _semaphore
    _semaphore = asyncio.Semaphore(CONCURRENCY_CAP)

    log.info("Scheduler started (concurrency cap: %d)", CONCURRENCY_CAP)

    exploits, teams, flag_format = await _load_db_state()
    last_poll = asyncio.get_event_loop().time()
    # exploit_id → monotonic timestamp of last dispatch
    last_dispatch: dict[int, float] = {}

    try:
        while True:
            now = asyncio.get_event_loop().time()

            # Refresh DB state on interval to pick up UI changes.
            if now - last_poll >= DB_POLL_INTERVAL:
                exploits, teams, flag_format = await _load_db_state()
                last_poll = now

            if teams:
                for exploit in exploits:
                    if exploit.id not in last_dispatch:
                        # First time seeing this exploit — make it due immediately.
                        last_dispatch[exploit.id] = now - exploit.period

                    if now - last_dispatch[exploit.id] >= exploit.period:
                        log.debug(
                            "Dispatching exploit '%s' against %d team(s)",
                            exploit.name,
                            len(teams),
                        )
                        for team in teams:
                            _fire(exploit, team, flag_format)
                        last_dispatch[exploit.id] = now

            # Drop timing entries for exploits that were disabled or deleted.
            active_ids = {e.id for e in exploits}
            for eid in list(last_dispatch):
                if eid not in active_ids:
                    del last_dispatch[eid]

            await asyncio.sleep(TICK_INTERVAL)

    except asyncio.CancelledError:
        log.info(
            "Scheduler stopping — cancelling %d in-flight task(s)", len(_running_tasks)
        )
        for task in list(_running_tasks):
            task.cancel()
        if _running_tasks:
            await asyncio.gather(*list(_running_tasks), return_exceptions=True)
        log.info("Scheduler stopped")
        raise
