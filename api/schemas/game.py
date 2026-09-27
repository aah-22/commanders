"""Response models for /v1/games/{game_id} and /v1/games/{game_id}/plays."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from api.schemas.season import DownDistanceCell


class Drive(BaseModel):
    drive: int
    posteam: str | None = None
    qtr: int | None = None
    start_seconds: int | None = None
    start_yardline_100: int | None = None
    plays: int
    yards: int
    epa: float | None = None
    result: str | None = None
    points: int | None = None
    points_against: int | None = None
    first_play_id: int
    last_play_id: int


class WinProbPoint(BaseModel):
    play_id: int | None = None
    qtr: int | None = None
    game_seconds_remaining: int
    home_wp: float


class GameDetail(BaseModel):
    game_id: str
    season: int
    week: int
    game_type: str
    gameday: str | None = None
    gametime: str | None = None
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    played: bool
    team: str
    prev_game_id: str | None = None
    next_game_id: str | None = None
    drives: list[Drive]
    win_prob: list[WinProbPoint]
    down_distance: list[DownDistanceCell]


class PlayRow(BaseModel):
    play_id: int
    fixed_drive: int | None = None
    qtr: int | None = None
    game_seconds_remaining: int | None = None
    posteam: str | None = None
    defteam: str | None = None
    down: int | None = None
    ydstogo: int | None = None
    yardline_100: int | None = None
    goal_to_go: int | None = None
    play_type: str | None = None
    desc: str | None = None
    yards_gained: int | None = None
    epa: float | None = None
    wp: float | None = None
    wpa: float | None = None
    success: float | None = None
    first_down: int | None = None
    touchdown: int | None = None
    sack: int | None = None
    interception: int | None = None
    fumble_lost: int | None = None
    penalty: int | None = None
    complete_pass: int | None = None
    shotgun: int | None = None
    no_huddle: int | None = None
    qb_dropback: int | None = None
    aborted_play: int | None = None
    pass_location: str | None = None
    run_location: str | None = None
    air_yards: float | None = None
    yards_after_catch: float | None = None
    posteam_score: int | None = None
    defteam_score: int | None = None


PlayKind = Literal["all", "scrimmage", "pass", "run", "special"]
Bucket = Literal["short", "mid", "long", "xlong"]


class GamePlays(BaseModel):
    game_id: str
    total: int
    plays: list[PlayRow]
