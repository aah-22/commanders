"""/v1/games/{game_id} (header, drives, win probability, down × distance) and /v1/games/{game_id}/plays (filtered)."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response

from api import db
from api.cache import cached
from api.config import get_settings
from api.queries import game as q
from api.routers.season import TEAM_RE
from api.schemas.game import Bucket, GameDetail, GamePlays, PlayKind

router = APIRouter(prefix="/v1/games", tags=["games"])
GAME_RE = re.compile(r"^\d{4}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$")


def _game_or_404(conn, game_id: str) -> dict:  # noqa: ANN001
    if not GAME_RE.match(game_id):
        raise HTTPException(422, "game_id looks like 2026_01_NYG_WAS")
    g = q.game(conn, game_id)
    if g is None:
        raise HTTPException(404, f"no game {game_id}")
    return g


@router.get("/{game_id}", response_model=GameDetail)
@cached
async def game_detail(request: Request, response: Response, game_id: str, team: str | None = None) -> GameDetail:
    if team and not TEAM_RE.match(team):
        raise HTTPException(422, "team must be a 2–3 letter upper-case abbreviation")
    with db.engine().connect() as conn:
        g = _game_or_404(conn, game_id)
        focus = q.focus_team(g, team or get_settings().team)
        rows = q.plays(conn, game_id)
        return GameDetail(
            **{k: g[k] for k in ("game_id", "season", "week", "game_type", "gameday", "gametime")},
            **{k: g[k] for k in ("home_team", "away_team", "home_score", "away_score")},
            played=g["result"] is not None,
            team=focus,
            **q.neighbours(conn, g, focus),
            drives=q.drives(rows, g),
            win_prob=q.win_prob(rows, g),
            down_distance=q.game_down_distance(conn, g, focus),
        )


@router.get("/{game_id}/plays", response_model=GamePlays)
@cached
async def game_plays(  # noqa: PLR0913
    request: Request,
    response: Response,
    game_id: str,
    posteam: Annotated[str | None, Query(pattern=TEAM_RE.pattern)] = None,
    down: Annotated[int | None, Query(ge=1, le=4)] = None,
    distance: Bucket | None = None,
    rz: bool = False,
    drive: Annotated[int | None, Query(ge=1)] = None,
    type: PlayKind = "all",  # noqa: A002
) -> GamePlays:
    with db.engine().connect() as conn:
        _game_or_404(conn, game_id)
        rows = q.plays(conn, game_id, posteam=posteam, down=down, distance=distance, rz=rz, drive=drive, kind=type)
        return GamePlays(game_id=game_id, total=len(rows), plays=rows)
