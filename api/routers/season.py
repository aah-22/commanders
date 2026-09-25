"""/v1/season/{season}/summary | league | games — the season dashboard's three reads, cached."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Request, Response

from api import db
from api.cache import cached
from api.config import get_settings
from api.queries import season as q
from api.schemas.season import LeagueSummary, SeasonGames, SeasonSummary

router = APIRouter(prefix="/v1/season", tags=["season"])
TEAM_RE = re.compile(r"^[A-Z]{2,3}$")


def _team(team: str | None) -> str:
    team = team or get_settings().team
    if not TEAM_RE.match(team):
        raise HTTPException(422, "team must be a 2–3 letter upper-case abbreviation")
    return team


def _season(season: int) -> int:
    if not 1999 <= season <= get_settings().season + 1:
        raise HTTPException(422, "season out of range")
    return season


def _games_or_404(conn, season: int) -> list[dict]:  # noqa: ANN001
    games = q.games(conn, season)
    if not games:
        raise HTTPException(404, f"no games for season {season}")
    return games


@router.get("/{season}/summary", response_model=SeasonSummary)
@cached
async def summary(
    request: Request, response: Response, season: int, team: str | None = Query(default=None)
) -> SeasonSummary:
    season, team = _season(season), _team(team)
    with db.engine().connect() as conn:
        games = _games_or_404(conn, season)
        upto = q.through_week(games)
        rows = q.team_weeks(conn, season)
        aggs = q.aggregates(rows, upto)
        return SeasonSummary(
            season=season,
            team=team,
            through_week=upto,
            league_teams=len(aggs),
            standing=q.standing(conn, season, team),
            weeks=[r for r in rows if r["team"] == team],
            aggregate=next((a for a in aggs if a["team"] == team), None),
            league_weekly=q.league_weekly(rows),
            next_game=q.next_game(games, team),
            down_distance=q.down_distance(conn, season, team),
        )


@router.get("/{season}/league", response_model=LeagueSummary)
@cached
async def league(request: Request, response: Response, season: int) -> LeagueSummary:
    season = _season(season)
    with db.engine().connect() as conn:
        games = _games_or_404(conn, season)
        upto = q.through_week(games)
        return LeagueSummary(season=season, through_week=upto, teams=q.aggregates(q.team_weeks(conn, season), upto))


@router.get("/{season}/games", response_model=SeasonGames)
@cached
async def season_games(
    request: Request, response: Response, season: int, team: str | None = Query(default=None)
) -> SeasonGames:
    season, team = _season(season), _team(team)
    with db.engine().connect() as conn:
        games = _games_or_404(conn, season)
        return SeasonGames(
            season=season, team=team, games=q.schedule_rows(games, q.team_weeks(conn, season, team), team)
        )
