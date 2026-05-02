from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"


# ── Config ────────────────────────────────────────────────────────────────────

class ConfigSetRequest(BaseModel):
    key: str
    value: dict[str, Any]


class ConfigResponse(BaseModel):
    key: str
    value: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ProtocolInfo(BaseModel):
    name: str
    display_name: str
    params_schema: dict[str, Any]


# ── Teams ─────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str
    ip: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    active: Optional[bool] = None


class TeamBulkImport(BaseModel):
    teams: list[TeamCreate]


class TeamResponse(BaseModel):
    id: int
    name: str
    ip: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Exploits ──────────────────────────────────────────────────────────────────

class ExploitUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    period: Optional[int] = None
    timeout: Optional[int] = None


class ExploitResponse(BaseModel):
    id: int
    name: str
    filename: str
    language: str
    enabled: bool
    period: int
    timeout: int
    last_run: Optional[datetime]
    created_at: datetime
    flags_total: int = 0
    flags_accepted: int = 0

    model_config = ConfigDict(from_attributes=True)


class ExploitRunResponse(BaseModel):
    id: int
    exploit_id: Optional[int]
    team_id: Optional[int]
    team_ip: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime]
    exit_code: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    flags_found: int

    model_config = ConfigDict(from_attributes=True)


# ── Flags ─────────────────────────────────────────────────────────────────────

class FlagResponse(BaseModel):
    id: int
    flag: str
    exploit_id: Optional[int]
    exploit_name: Optional[str] = None
    team_id: Optional[int]
    team_ip: Optional[str] = None
    status: str
    response: Optional[str]
    captured_at: datetime
    submitted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class FlagListResponse(BaseModel):
    total: int
    items: list[FlagResponse]


# ── Stats ─────────────────────────────────────────────────────────────────────

class StatsOverview(BaseModel):
    total_flags: int
    accepted: int
    rejected: int
    pending: int
    exploits_active: int
    teams_active: int


class TimelinePoint(BaseModel):
    minute: datetime
    count: int


class TeamStats(BaseModel):
    team_id: int
    team_name: str
    team_ip: str
    flags_accepted: int


class ExploitStats(BaseModel):
    exploit_id: int
    exploit_name: str
    flags_accepted: int
    flags_total: int


# ── Manual submit ─────────────────────────────────────────────────────────────

class ManualSubmitRequest(BaseModel):
    flags: list[str]


class ManualSubmitResult(BaseModel):
    flag: str
    status: str
    response: str
