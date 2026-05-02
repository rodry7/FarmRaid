import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from config_manager import get_config
from database import get_db
from models import Exploit, Flag, Team
from protocols import get_protocol
from schemas import (
    FlagListResponse,
    FlagResponse,
    ManualSubmitRequest,
    ManualSubmitResult,
)

router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("", response_model=FlagListResponse)
async def list_flags(
    status: Optional[str] = Query(None),
    exploit_id: Optional[int] = Query(None),
    team_id: Optional[int] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> FlagListResponse:
    q = select(Flag)
    count_q = select(func.count()).select_from(Flag)

    if status:
        q = q.where(Flag.status == status)
        count_q = count_q.where(Flag.status == status)
    if exploit_id is not None:
        q = q.where(Flag.exploit_id == exploit_id)
        count_q = count_q.where(Flag.exploit_id == exploit_id)
    if team_id is not None:
        q = q.where(Flag.team_id == team_id)
        count_q = count_q.where(Flag.team_id == team_id)

    total_res = await db.execute(count_q)
    total = total_res.scalar_one()

    flags_res = await db.execute(
        q.order_by(Flag.captured_at.desc()).limit(limit).offset(offset)
    )
    flags = flags_res.scalars().all()

    items: list[FlagResponse] = []
    for flag in flags:
        exploit_name: Optional[str] = None
        team_ip: Optional[str] = None

        if flag.exploit_id:
            e_res = await db.execute(
                select(Exploit).where(Exploit.id == flag.exploit_id)
            )
            e = e_res.scalar_one_or_none()
            if e:
                exploit_name = e.name

        if flag.team_id:
            t_res = await db.execute(select(Team).where(Team.id == flag.team_id))
            t = t_res.scalar_one_or_none()
            if t:
                team_ip = t.ip

        items.append(
            FlagResponse(
                id=flag.id,
                flag=flag.flag,
                exploit_id=flag.exploit_id,
                exploit_name=exploit_name,
                team_id=flag.team_id,
                team_ip=team_ip,
                status=flag.status,
                response=flag.response,
                captured_at=flag.captured_at,
                submitted_at=flag.submitted_at,
            )
        )

    return FlagListResponse(total=total, items=items)


@router.post("/submit", response_model=list[ManualSubmitResult])
async def manual_submit(
    body: ManualSubmitRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[ManualSubmitResult]:
    flags = list(dict.fromkeys(f.strip() for f in body.flags if f.strip()))
    if not flags:
        return []

    # Insert new flags; skip any that already exist in the DB.
    for flag_str in flags:
        await db.execute(
            pg_insert(Flag)
            .values(flag=flag_str, status="pending")
            .on_conflict_do_nothing(index_elements=["flag"])
        )
    await db.commit()

    res = await db.execute(select(Flag).where(Flag.flag.in_(flags)))
    flag_map: dict[str, Flag] = {f.flag: f for f in res.scalars().all()}

    submission_cfg = await get_config(db, "submission") or {}
    protocol_name: str = submission_cfg.get("protocol", "")
    protocol_params: dict = submission_cfg.get("params") or {}

    if not protocol_name:
        return [
            ManualSubmitResult(
                flag=f, status="error", response="no protocol configured"
            )
            for f in flags
        ]

    try:
        protocol = get_protocol(protocol_name, protocol_params)
        results = await asyncio.wait_for(protocol.submit(flags), timeout=60)
    except asyncio.TimeoutError:
        return [
            ManualSubmitResult(flag=f, status="error", response="submission timed out")
            for f in flags
        ]
    except Exception as exc:
        return [
            ManualSubmitResult(flag=f, status="error", response=str(exc)) for f in flags
        ]

    now = datetime.now(timezone.utc)
    output: list[ManualSubmitResult] = []
    for flag_str, status, response in results:
        flag_obj = flag_map.get(flag_str)
        if flag_obj:
            await db.execute(
                update(Flag)
                .where(Flag.id == flag_obj.id)
                .values(status=status, response=response[:500], submitted_at=now)
            )
        output.append(
            ManualSubmitResult(flag=flag_str, status=status, response=response)
        )
    await db.commit()

    return output
