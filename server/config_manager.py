from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Config


async def get_config(db: AsyncSession, key: str) -> Optional[dict]:
    result = await db.execute(select(Config).where(Config.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def get_all_config(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(Config))
    rows = result.scalars().all()
    return {row.key: row.value for row in rows}


async def set_config(db: AsyncSession, key: str, value: dict) -> Config:
    stmt = (
        pg_insert(Config)
        .values(key=key, value=value)
        .on_conflict_do_update(index_elements=["key"], set_={"value": value})
        .returning(Config)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def seed_defaults(db: AsyncSession) -> None:
    """Insert default config rows if they don't already exist."""
    from auth import hash_password

    defaults = {
        "competition": {
            "name": "CTF Competition",
            "flag_format": r"[A-Z0-9]{31}=",
            "flag_lifetime": 300,
            "timezone": "UTC",
        },
        "submission": {
            "protocol": "forcad_tcp",
            "params": {},
            "submit_flag_limit": 100,
            "submit_period": 10,
        },
        "server": {
            "password_hash": hash_password("changeme"),
            "setup_complete": False,
        },
    }

    existing = await get_all_config(db)
    for key, value in defaults.items():
        if key not in existing:
            stmt = (
                pg_insert(Config).values(key=key, value=value).on_conflict_do_nothing()
            )
            await db.execute(stmt)

    await db.commit()
