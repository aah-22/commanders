"""Response models for /v1/season/*. `TeamGameSummary` mirrors gm.team_game_summary column for column."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, create_model
from sqlalchemy import Boolean, Float, Integer

from db import schema


def _py(col) -> type:  # noqa: ANN001
    if isinstance(col.type, Boolean):
        return bool
    if isinstance(col.type, Integer):
        return int
    if isinstance(col.type, Float):
        return float
    return str


TeamGameSummary = create_model(
    "TeamGameSummary",
    gameday=(str | None, None),
    **{c.name: (_py(c) | None, None) for c in schema.team_game_summary.c},
)


class Standing(BaseModel):
    season: int
    week: int
    team: str
    conf: str | None = None
    division: str | None = None
    wins: int
    losses: int
    ties: int
    games_played: int
    pf: int
    pa: int
    point_diff: int
    win_pct: float | None = None
    pythag_win_pct: float | None = None
    div_rank: int | None = None
    conf_rank: int | None = None


class TeamSeasonAggregate(BaseModel):
    """Season-to-date, plays-weighted (PROE by neutral plays, points per drive by drives)."""

    team: str
    games: int
    off_epa_per_play: float | None = None
    off_success_rate: float | None = None
    off_explosive_rate: float | None = None
    off_proe: float | None = None
    off_pass_epa_per_play: float | None = None
    off_rush_epa_per_play: float | None = None
    off_points_per_drive: float | None = None
    def_epa_per_play: float | None = None
    def_success_rate: float | None = None
    def_explosive_rate: float | None = None
    def_pass_epa_per_play: float | None = None
    def_rush_epa_per_play: float | None = None
    def_points_per_drive: float | None = None
    ranks: dict[str, int] = {}


class NextGame(BaseModel):
    game_id: str
    week: int
    opponent: str
    is_home: bool
    gameday: str | None = None
    gametime: str | None = None


class LeagueWeek(BaseModel):
    week: int
    teams: int
    off_epa_p25: float | None = None
    off_epa_median: float | None = None
    off_epa_p75: float | None = None
    def_epa_p25: float | None = None
    def_epa_median: float | None = None
    def_epa_p75: float | None = None


class DownDistanceCell(BaseModel):
    down: int
    bucket: Literal["short", "mid", "long", "xlong"]
    team_rate: float | None = None
    team_n: int = 0
    league_rate: float | None = None
    league_n: int = 0


class SeasonSummary(BaseModel):
    season: int
    team: str
    through_week: int | None = None
    league_teams: int
    standing: Standing | None = None
    weeks: list[TeamGameSummary]  # type: ignore[valid-type]
    aggregate: TeamSeasonAggregate | None = None
    league_weekly: list[LeagueWeek]
    next_game: NextGame | None = None
    down_distance: list[DownDistanceCell]


class LeagueSummary(BaseModel):
    season: int
    through_week: int | None = None
    teams: list[TeamSeasonAggregate]


class GameRow(BaseModel):
    game_id: str
    week: int
    game_type: str
    gameday: str | None = None
    gametime: str | None = None
    opponent: str
    is_home: bool
    points_for: int | None = None
    points_against: int | None = None
    result: str | None = None
    summary: TeamGameSummary | None = None  # type: ignore[valid-type]


class SeasonGames(BaseModel):
    season: int
    team: str
    games: list[GameRow]
