"""SQLAlchemy 2.0 ORM shared by the API and the jobs. Phase 0 carries the bookkeeping and the game table;
phase 1 adds the nflverse mirrors (nfl.*), phase 2+ the derived gm.* and ml.* tables (see docs/commanders-build-guide.md §5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMAS = ("nfl", "gm", "ml", "ops")


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    """One row per job invocation (ingest / derive / train / score), mirroring the MLflow run."""

    __tablename__ = "pipeline_runs"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64))
    season: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="running")
    rows: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Game(Base):
    """nflverse schedules, one row per game (the spread/total/moneyline columns are deliberately not mirrored)."""

    __tablename__ = "games"
    __table_args__ = {"schema": "nfl"}

    game_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    game_type: Mapped[str] = mapped_column(String(8))
    gameday: Mapped[str | None] = mapped_column(String(10))
    gametime: Mapped[str | None] = mapped_column(String(8))
    home_team: Mapped[str] = mapped_column(String(4), index=True)
    away_team: Mapped[str] = mapped_column(String(4), index=True)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[int | None] = mapped_column(Integer)  # home margin; NULL until played
    total: Mapped[int | None] = mapped_column(Integer)
    roof: Mapped[str | None] = mapped_column(String(16))
    surface: Mapped[str | None] = mapped_column(String(16))
    stadium: Mapped[str | None] = mapped_column(Text)
