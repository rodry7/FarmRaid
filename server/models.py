from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    flags: Mapped[list["Flag"]] = relationship("Flag", back_populates="team")
    exploit_runs: Mapped[list["ExploitRun"]] = relationship("ExploitRun", back_populates="team")


class Exploit(Base):
    __tablename__ = "exploits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)  # 'python' | 'bash'
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    period: Mapped[int] = mapped_column(Integer, server_default="120", nullable=False)
    timeout: Mapped[int] = mapped_column(Integer, server_default="30", nullable=False)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    flags: Mapped[list["Flag"]] = relationship("Flag", back_populates="exploit")
    exploit_runs: Mapped[list["ExploitRun"]] = relationship("ExploitRun", back_populates="exploit")


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    flag: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    exploit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("exploits.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, server_default="pending", nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    exploit: Mapped[Optional["Exploit"]] = relationship("Exploit", back_populates="flags")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="flags")


class ExploitRun(Base):
    __tablename__ = "exploit_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    exploit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("exploits.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flags_found: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    exploit: Mapped[Optional["Exploit"]] = relationship("Exploit", back_populates="exploit_runs")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="exploit_runs")
