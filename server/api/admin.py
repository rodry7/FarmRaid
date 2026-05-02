from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Config

router = APIRouter(prefix="/admin", tags=["admin"])

_DEFAULT_COMPETITION = {
    "name": "CTF Competition",
    "flag_format": r"[A-Z0-9]{31}=",
    "flag_lifetime": 300,
    "timezone": "UTC",
}

_DEFAULT_SUBMISSION = {
    "protocol": "forcad_tcp",
    "params": {},
    "submit_flag_limit": 100,
    "submit_period": 10,
}


@router.delete("/reset")
async def reset_database(
    mode: Literal["data", "full"] = Query(
        "data",
        description="'data' clears flags/runs only; 'full' also wipes teams, exploits, and resets config",
    ),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    if mode == "data":
        # Remove only operational data — teams and exploits are kept.
        await db.execute(text("TRUNCATE TABLE exploit_runs, flags RESTART IDENTITY"))
    else:
        # Full wipe: clear child tables first (they reference exploits/teams),
        # then parent tables, then reset config to defaults (preserving the password).
        await db.execute(
            text(
                "TRUNCATE TABLE exploit_runs, flags, exploits, teams RESTART IDENTITY CASCADE"
            )
        )
        for key, value in (
            ("competition", _DEFAULT_COMPETITION),
            ("submission", _DEFAULT_SUBMISSION),
        ):
            await db.execute(
                pg_insert(Config)
                .values(key=key, value=value)
                .on_conflict_do_update(index_elements=["key"], set_={"value": value})
            )

    await db.commit()
    return {"message": "Reset complete", "mode": mode}
