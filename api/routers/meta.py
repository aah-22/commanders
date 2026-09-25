"""Liveness, readiness and data freshness."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select

from api import db
from api.cache import cached
from api.config import get_settings
from db import schema

log = logging.getLogger(__name__)
router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    ok = db.ping()
    return {"status": "ok" if ok else "degraded", "database": ok}


@router.get("/v1/meta/freshness")
@cached
async def freshness(request: Request, response: Response) -> dict:
    """Latest ingest run and the season/week the data runs through (empty until the first ingest)."""
    s = get_settings()
    out = {"season": s.season, "team": s.team, "last_ingest": None, "through_week": None}
    runs, games = schema.PipelineRun.__table__, schema.Game.__table__
    try:
        with db.engine().connect() as c:
            row = c.execute(
                select(runs.c.finished_at)
                .where(runs.c.kind == "ingest", runs.c.status == "ok")
                .order_by(runs.c.finished_at.desc())
                .limit(1)
            ).first()
            if row:
                out["last_ingest"] = str(row[0])
            out["through_week"] = c.execute(
                select(func.max(games.c.week)).where(games.c.season == s.season, games.c.result.is_not(None))
            ).scalar()
    except Exception as exc:  # noqa: BLE001  (no schema yet)
        log.info("freshness unavailable: %s", exc)
    return out
