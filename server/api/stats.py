from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Exploit, Flag, Team
from schemas import ExploitStats, StatsOverview, TeamStats, TimelinePoint

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
async def overview(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> StatsOverview:
    counts: dict[str, int] = {}
    for s in ("pending", "accepted", "rejected"):
        res = await db.execute(select(func.count()).select_from(Flag).where(Flag.status == s))
        counts[s] = res.scalar_one() or 0

    total_res = await db.execute(select(func.count()).select_from(Flag))
    total = total_res.scalar_one() or 0

    active_exploits_res = await db.execute(
        select(func.count()).select_from(Exploit).where(Exploit.enabled.is_(True))
    )
    active_exploits = active_exploits_res.scalar_one() or 0

    active_teams_res = await db.execute(
        select(func.count()).select_from(Team).where(Team.active.is_(True))
    )
    active_teams = active_teams_res.scalar_one() or 0

    return StatsOverview(
        total_flags=total,
        accepted=counts.get("accepted", 0),
        rejected=counts.get("rejected", 0),
        pending=counts.get("pending", 0),
        exploits_active=active_exploits,
        teams_active=active_teams,
    )


@router.get("/timeline", response_model=list[TimelinePoint])
async def timeline(
    minutes: int = Query(30, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[TimelinePoint]:
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    # Truncate captured_at to minute granularity and count accepted flags
    res = await db.execute(
        select(
            func.date_trunc("minute", Flag.captured_at).label("minute"),
            func.count().label("count"),
        )
        .where(Flag.captured_at >= since, Flag.status == "accepted")
        .group_by(func.date_trunc("minute", Flag.captured_at))
        .order_by(func.date_trunc("minute", Flag.captured_at))
    )
    return [TimelinePoint(minute=row.minute, count=row.count) for row in res]


@router.get("/by_team", response_model=list[TeamStats])
async def by_team(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[TeamStats]:
    res = await db.execute(
        select(
            Team.id,
            Team.name,
            Team.ip,
            func.count(Flag.id).label("flags_accepted"),
        )
        .outerjoin(Flag, (Flag.team_id == Team.id) & (Flag.status == "accepted"))
        .group_by(Team.id, Team.name, Team.ip)
        .order_by(func.count(Flag.id).desc())
    )
    return [
        TeamStats(
            team_id=row.id,
            team_name=row.name,
            team_ip=row.ip,
            flags_accepted=row.flags_accepted,
        )
        for row in res
    ]


@router.get("/by_exploit", response_model=list[ExploitStats])
async def by_exploit(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[ExploitStats]:
    accepted_res = await db.execute(
        select(
            Exploit.id,
            Exploit.name,
            func.count(Flag.id).label("flags_accepted"),
        )
        .outerjoin(Flag, (Flag.exploit_id == Exploit.id) & (Flag.status == "accepted"))
        .group_by(Exploit.id, Exploit.name)
        .order_by(func.count(Flag.id).desc())
    )
    accepted_rows = {row.id: row.flags_accepted for row in accepted_res}

    total_res = await db.execute(
        select(
            Exploit.id,
            Exploit.name,
            func.count(Flag.id).label("flags_total"),
        )
        .outerjoin(Flag, Flag.exploit_id == Exploit.id)
        .group_by(Exploit.id, Exploit.name)
        .order_by(func.count(Flag.id).desc())
    )

    return [
        ExploitStats(
            exploit_id=row.id,
            exploit_name=row.name,
            flags_accepted=accepted_rows.get(row.id, 0),
            flags_total=row.flags_total,
        )
        for row in total_res
    ]
