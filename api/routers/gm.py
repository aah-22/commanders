"""/v1/gm/acquisitions | need | targets and /v1/models."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response

from api import db
from api.cache import cached
from api.config import get_settings
from api.queries import gm as q
from api.routers.season import _season
from api.schemas.gm import Acquisitions, Models, Need, Targets
from ingest.derive import positions as pos

router = APIRouter(tags=["gm"])


def _pos(position: str | None) -> str | None:
    if position and position not in pos.GROUPS:
        raise HTTPException(422, f"position must be one of {', '.join(pos.GROUPS)}")
    return position


@router.get("/v1/gm/acquisitions", response_model=Acquisitions)
@cached
async def acquisitions(
    request: Request, response: Response, season: int | None = None, since: int | None = None
) -> Acquisitions:
    s = get_settings()
    season = _season(season or s.season)
    since = since or season - 1
    with db.engine().connect() as conn:
        return Acquisitions(season=season, team=s.team, since=since, cards=q.acquisitions(conn, season, s.team, since))


@router.get("/v1/gm/need", response_model=Need)
@cached
async def need(request: Request, response: Response, season: int | None = None) -> Need:
    s = get_settings()
    season = _season(season or s.season)
    with db.engine().connect() as conn:
        return Need(season=season, team=s.team, groups=q.need(conn, season, s.team))


@router.get("/v1/gm/targets", response_model=Targets)
@cached
async def targets(
    request: Request,
    response: Response,
    season: int | None = None,
    position: str | None = None,
    per_group: Annotated[int, Query(ge=1, le=50)] = 8,
) -> Targets:
    s = get_settings()
    season, position = _season(season or s.season), _pos(position)
    with db.engine().connect() as conn:
        out = q.targets(conn, season, s.team, position, per_group)
        return Targets(season=season, team=s.team, position=position, **out)


@router.get("/v1/models", response_model=Models)
@cached
async def models(request: Request, response: Response) -> Models:
    with db.engine().connect() as conn:
        out = q.models(conn)
    return Models(
        experiment=os.environ.get("MLFLOW_EXPERIMENT", "commanders"),
        tracking="https://mlflow.caabi.dev",
        **out,
    )
