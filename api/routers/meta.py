"""Liveness, readiness and data freshness."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from api import db
from api.cache import cached
from api.config import get_settings

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
    try:
        with db.engine().connect() as c:
            row = c.execute(
                text(
                    "SELECT finished_at, detail FROM ops.pipeline_runs WHERE kind='ingest' AND status='ok' ORDER BY finished_at DESC LIMIT 1"
                )
            ).first()
            if row:
                out["last_ingest"] = str(row[0])
            wk = c.execute(
                text("SELECT max(week) FROM nfl.games WHERE season=:s AND result IS NOT NULL"), {"s": s.season}
            ).scalar()
            out["through_week"] = wk
    except Exception as exc:  # noqa: BLE001  (no schema yet, or sqlite in tests)
        log.info("freshness unavailable: %s", exc)
    return out
