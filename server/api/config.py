from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import authenticate, create_access_token, get_current_user, hash_password
from config_manager import get_all_config, get_config, set_config
from database import get_db
from protocols import PROTOCOL_INFO
from schemas import ChangePasswordRequest, ConfigSetRequest, LoginRequest, ProtocolInfo, TokenResponse

router = APIRouter(tags=["auth", "config"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    if not await authenticate(body.password, db):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    token = create_access_token({"sub": "admin"})
    return TokenResponse(token=token)


@router.get("/auth/verify")
async def verify(_: dict = Depends(get_current_user)) -> dict:
    return {"valid": True}


@router.get("/config")
async def get_config_all(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return await get_all_config(db)


@router.post("/config")
async def update_config(
    body: ConfigSetRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict[str, Any]:
    row = await set_config(db, body.key, body.value)
    return {"key": row.key, "value": row.value}


@router.post("/auth/change_password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    server_cfg = await get_config(db, "server") or {}
    server_cfg["password_hash"] = hash_password(body.new_password)
    await set_config(db, "server", server_cfg)
    return {"ok": True}


@router.get("/config/protocols", response_model=list[ProtocolInfo])
async def list_protocols(_: dict = Depends(get_current_user)) -> list[ProtocolInfo]:
    return [
        ProtocolInfo(name=p["name"], display_name=p["display_name"], params_schema=p["params_schema"])
        for p in PROTOCOL_INFO
    ]
