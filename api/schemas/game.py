"""Response models for /v1/games/{game_id}, /v1/games/{game_id}/plays and /v1/games/{game_id}/insights."""

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
    half_seconds_remaining: int | None = None
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
    xpass: float | None = None
    success: float | None = None
    first_down: int | None = None
    touchdown: int | None = None
    sack: int | None = None
    qb_hit: int | None = None
    qb_scramble: int | None = None
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
    series: int | None = None
    passer_player_id: str | None = None
    rusher_player_id: str | None = None
    receiver_player_id: str | None = None
    posteam_score: int | None = None
    defteam_score: int | None = None
    # FTN charting, null when the play has no charting row (special teams, or a week not charted yet)
    charted: int | None = None  # 1 when a charting row was found
    qb_location: str | None = None  # U = under center, S = shotgun, P = pistol
    n_defense_box: int | None = None
    n_pass_rushers: int | None = None
    n_blitzers: int | None = None
    read_thrown: str | None = None
    is_play_action: int | None = None
    is_screen_pass: int | None = None
    is_rpo: int | None = None
    is_motion: int | None = None
    is_qb_out_of_pocket: int | None = None
    is_drop: int | None = None
    is_interception_worthy: int | None = None
    is_throw_away: int | None = None


PlayKind = Literal["all", "scrimmage", "pass", "run", "special"]
Bucket = Literal["short", "mid", "long", "xlong"]
# One-tap narrowings of the play list. The FTN-backed ones (play_action … light_box) match nothing for a game that
# has no charting rows yet; `pressure` is a sack or a QB hit, `explosive` a 20+ yard pass or 12+ yard run,
# `big_swing` a win-probability move of at least 10 points either way.
PlayTag = Literal[
    "play_action",
    "screen",
    "rpo",
    "motion",
    "blitz",
    "light_box",
    "pressure",
    "scramble",
    "explosive",
    "no_huddle",
    "penalty",
    "big_swing",
]


class GamePlays(BaseModel):
    game_id: str
    total: int
    plays: list[PlayRow]


# --------------------------------------------------------------------------- insights
# Every number on the insights page is a `Stat`: the team's value in this game, the plays behind it (`n`), the league's
# season-to-date value for the same definition (through the last complete week) and, where gm.team_game_summary ranks
# the metric, the rank among the teams that played that week. `kind` says how to print it, `better` whether a higher
# value is good, bad or neither (tendencies such as a pass rate have no valence).


class Stat(BaseModel):
    key: str
    label: str
    value: float | None = None
    n: int = 0
    league: float | None = None
    league_n: int = 0
    rank: int | None = None
    teams: int | None = None
    kind: Literal["rate", "epa", "count", "number"] = "rate"
    better: Literal["high", "low", "none"] = "none"


class Share(BaseModel):
    """One part of a `Split`: its plays, its share of the split's `n`, and the league's share."""

    key: str
    label: str
    count: int = 0
    share: float | None = None
    league_share: float | None = None


class Split(BaseModel):
    """A part-to-whole breakdown (QB alignment, pass direction, target depth, box counts) with the league's shares."""

    key: str
    label: str
    n: int = 0
    league_n: int = 0
    parts: list[Share]


class QuarterLine(BaseModel):
    qtr: int
    label: str  # Q1 … Q4, OT
    points: int | None = None
    plays: int = 0
    epa_per_play: float | None = None
    success_rate: float | None = None


class ImpactPlayer(BaseModel):
    """A player's offensive involvement in the game: every clean pass or run he threw, carried or was targeted on."""

    gsis_id: str
    name: str | None = None
    position: str | None = None
    team: str
    plays: int = 0
    as_passer: int = 0
    as_rusher: int = 0
    as_receiver: int = 0
    yards: int = 0
    epa: float | None = None
    wpa: float | None = None
    big_plays: int = 0  # plays with |EPA| of at least 1


class TeamInsights(BaseModel):
    """One side of the game. `efficiency` is what the offense produced (EPA / play, success, explosive, points per
    drive …), `tendencies` what it chose (pass rate, PROE, alignment, play action, screens, motion, tempo …), `by_down`
    its pass rate per down, `splits` its part-to-whole breakdowns (QB alignment, dropback vs run, pass and run direction,
    target depth, box counts faced), `situations` third and fourth down, red zone, late downs, turnovers and sacks,
    `defense` what its defense allowed and generated (EPA, success, pressure, blitz rate …) with `defense_splits` the
    box counts it showed and the rushers it sent, and `players` the offense's most involved players, the most win
    probability moved first."""

    team: str
    opponent: str
    is_home: bool
    points: int | None = None
    quarters: list[QuarterLine]
    efficiency: list[Stat]
    tendencies: list[Stat]
    by_down: list[Stat]
    splits: list[Split]
    situations: list[Stat]
    defense: list[Stat]
    defense_splits: list[Split]
    players: list[ImpactPlayer]


class ImpactPlay(BaseModel):
    play_id: int
    drive: int | None = None
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
    wpa: float | None = None
    home_wp_before: float | None = None
    home_wp_after: float | None = None
    touchdown: int | None = None
    interception: int | None = None
    fumble_lost: int | None = None
    sack: int | None = None
    penalty: int | None = None
    fourth_down: bool = False
    posteam_score: int | None = None
    defteam_score: int | None = None


class ScoringPlay(BaseModel):
    """A play that changed the score; a touchdown's row includes the try that followed it."""

    play_id: int
    qtr: int | None = None
    game_seconds_remaining: int | None = None
    team: str
    desc: str | None = None
    points: int
    home_score: int  # after the play (and its try)
    away_score: int


class GameInsights(BaseModel):
    game_id: str
    season: int
    week: int
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    played: bool
    team: str  # the focus team: teams[0]
    opponent: str  # teams[1]
    league_through_week: int | None = None  # the league baselines run through this week
    league_teams: int = 0
    charted: bool = False  # FTN charting rows exist for this game
    teams: list[TeamInsights]
    impact_plays: list[ImpactPlay]  # the biggest win-probability swings, largest first
    scoring: list[ScoringPlay]  # in game order
