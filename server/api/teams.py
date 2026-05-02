from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Team
from schemas import TeamBulkImport, TeamCreate, TeamResponse, TeamUpdate

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[Team]:
    result = await db.execute(select(Team).order_by(Team.id))
    return list(result.scalars().all())


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Team:
    team = Team(name=body.name, ip=body.ip)
    db.add(team)
    try:
        await db.commit()
        await db.refresh(team)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="IP already exists"
        )
    return team


@router.post(
    "/bulk", response_model=list[TeamResponse], status_code=status.HTTP_201_CREATED
)
async def bulk_import_teams(
    body: TeamBulkImport,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[Team]:
    # INSERT … ON CONFLICT DO NOTHING is idempotent by IP — no mid-loop rollbacks.
    for entry in body.teams:
        stmt = (
            pg_insert(Team)
            .values(name=entry.name, ip=entry.ip)
            .on_conflict_do_nothing(index_elements=["ip"])
        )
        await db.execute(stmt)
    await db.commit()

    ips = [entry.ip for entry in body.teams]
    result = await db.execute(select(Team).where(Team.ip.in_(ips)).order_by(Team.id))
    return list(result.scalars().all())


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    body: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Team:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    if body.name is not None:
        team.name = body.name
    if body.ip is not None:
        team.ip = body.ip
    if body.active is not None:
        team.active = body.active

    try:
        await db.commit()
        await db.refresh(team)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="IP already exists"
        )
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> None:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    await db.execute(delete(Team).where(Team.id == team_id))
    await db.commit()
