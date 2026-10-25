"""Read-side queries for one game: the header row, every play (with the explorer's filters), drives folded from the
plays in Python, and the win-probability trace. A game is at most ~200 rows, so the folding happens here, not in SQL."""

from __future__ import annotations

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.engine import Connection

from api.queries.season import down_distance
from db import schema
from ingest.derive.filters import DISTANCE_BUCKETS

G = schema.Game.__table__
P = schema.plays
F = schema.ftn_charting

SCRIMMAGE = ("pass", "run")
SPECIAL = ("kickoff", "punt", "field_goal", "extra_point")
PLAY_TYPES = {"all": None, "scrimmage": SCRIMMAGE, "pass": ("pass",), "run": ("run",), "special": SPECIAL}
PLAY_COLUMNS = [
    "play_id",
    "fixed_drive",
    "qtr",
    "game_seconds_remaining",
    "half_seconds_remaining",
    "posteam",
    "defteam",
    "down",
    "ydstogo",
    "yardline_100",
    "goal_to_go",
    "play_type",
    "desc",
    "yards_gained",
    "epa",
    "wp",
    "wpa",
    "xpass",
    "success",
    "first_down",
    "touchdown",
    "sack",
    "qb_hit",
    "qb_scramble",
    "interception",
    "fumble_lost",
    "penalty",
    "complete_pass",
    "shotgun",
    "no_huddle",
    "qb_dropback",
    "aborted_play",
    "pass_location",
    "run_location",
    "air_yards",
    "yards_after_catch",
    "series",
    "passer_player_id",
    "rusher_player_id",
    "receiver_player_id",
    "posteam_score",
    "defteam_score",
    "total_home_score",
    "total_away_score",
    "fixed_drive_result",
]
# FTN charting columns joined onto every play (null when the play has no charting row)
FTN_COLUMNS = [
    "qb_location",
    "n_defense_box",
    "n_pass_rushers",
    "n_blitzers",
    "read_thrown",
    "is_play_action",
    "is_screen_pass",
    "is_rpo",
    "is_motion",
    "is_qb_out_of_pocket",
    "is_drop",
    "is_interception_worthy",
    "is_throw_away",
]
# `tag` → the one-tap narrowings of the play list (api/schemas/game.py `PlayTag`)
TAGS = {
    "play_action": F.c.is_play_action == 1,
    "screen": F.c.is_screen_pass == 1,
    "rpo": F.c.is_rpo == 1,
    "motion": F.c.is_motion == 1,
    "blitz": F.c.n_blitzers >= 1,
    "light_box": F.c.n_defense_box.between(3, 6),
    "pressure": or_(P.c.sack == 1, P.c.qb_hit == 1),
    "scramble": P.c.qb_scramble == 1,
    "explosive": or_(
        and_(P.c.play_type == "pass", P.c.yards_gained >= 20), and_(P.c.play_type == "run", P.c.yards_gained >= 12)
    ),
    "no_huddle": P.c.no_huddle == 1,
    "penalty": P.c.penalty == 1,
    "big_swing": func.abs(P.c.wpa) >= 0.10,
}


def game(conn: Connection, game_id: str) -> dict | None:
    row = conn.execute(select(G).where(G.c.game_id == game_id)).first()
    return dict(row._mapping) if row else None


def plays(  # noqa: PLR0913
    conn: Connection,
    game_id: str,
    *,
    posteam: str | None = None,
    down: int | None = None,
    distance: str | None = None,
    rz: bool = False,
    drive: int | None = None,
    kind: str = "all",
    qtr: int | None = None,
    tag: str | None = None,
) -> list[dict]:
    """The game's plays in game order with their FTN charting columns, narrowed by the explorer's filters (all
    optional; `qtr` 5 is overtime, `tag` one of `TAGS`). `charted` says whether a charting row was found."""
    stmt = (
        select(
            *[P.c[c] for c in PLAY_COLUMNS],
            *[F.c[c] for c in FTN_COLUMNS],
            case((F.c.play_id.is_not(None), 1), else_=0).label("charted"),
        )
        .select_from(P.outerjoin(F, and_(P.c.game_id == F.c.game_id, P.c.play_id == F.c.play_id)))
        .where(P.c.game_id == game_id)
    )
    if posteam:
        stmt = stmt.where(P.c.posteam == posteam)
    if down:
        stmt = stmt.where(P.c.down == down)
    if distance:
        lo, hi = next((lo, hi) for name, lo, hi in DISTANCE_BUCKETS if name == distance)
        stmt = stmt.where(P.c.ydstogo.between(lo, hi))
    if rz:
        stmt = stmt.where(P.c.yardline_100 <= 20)
    if drive:
        stmt = stmt.where(P.c.fixed_drive == drive)
    types = PLAY_TYPES[kind]
    if types:
        stmt = stmt.where(P.c.play_type.in_(types))
    if qtr:
        stmt = stmt.where(P.c.qtr >= 5) if qtr >= 5 else stmt.where(P.c.qtr == qtr)
    if tag:
        stmt = stmt.where(TAGS[tag])
    stmt = stmt.order_by(P.c.fixed_drive, P.c.play_id)
    return [dict(r._mapping) for r in conn.execute(stmt)]


def running_scores(rows: list[dict]) -> list[tuple[int, int]]:
    """The score after each play as (home, away). nflverse's `total_home_score` / `total_away_score` are the score
    after the play, but a dead-ball row (the kickoff after a field goal, END QUARTER, a timeout) sometimes still carries
    the score from before it, so the running maximum is the honest reading; scores never go down."""
    out: list[tuple[int, int]] = []
    home = away = 0
    for r in rows:
        home = max(home, r.get("total_home_score") or 0)
        away = max(away, r.get("total_away_score") or 0)
        out.append((home, away))
    return out


def _pick(pair: tuple[int, int], team: str | None, g: dict) -> int:
    return pair[0] if team == g["home_team"] else pair[1]


def drives(rows: list[dict], g: dict) -> list[dict]:
    """One row per fixed_drive. nflverse's `total_home_score` / `total_away_score` are the score after each play, so
    `points` is the offense's total after the drive's last play (the final score for the last drive) minus its total
    after the play before the drive began; `points_against` catches a defensive score on the same drive. Play, yard and
    EPA counts cover pass and run plays only. `rows` must be in game order (fixed_drive, play_id), as `plays` returns."""
    by_drive: dict[int, list[int]] = {}
    for i, r in enumerate(rows):
        if r["fixed_drive"] is not None:
            by_drive.setdefault(r["fixed_drive"], []).append(i)
    ordered = sorted(by_drive)
    run = running_scores(rows)
    out = []
    for n, d in enumerate(ordered):
        idx = sorted(by_drive[d], key=lambda i: rows[i]["play_id"])
        ps = [rows[i] for i in idx]
        first, last = ps[0], ps[-1]
        team = next((p["posteam"] for p in ps if p["posteam"]), None)
        opp = g["away_team"] if team == g["home_team"] else g["home_team"]
        scrim = [p for p in ps if p["play_type"] in SCRIMMAGE]
        start = next(
            (p["yardline_100"] for p in ps if p["play_type"] != "kickoff" and p["yardline_100"] is not None), None
        )
        after = run[idx[-1]] if n + 1 < len(ordered) else (g["home_score"], g["away_score"])
        before = run[idx[0] - 1] if idx[0] > 0 else (0, 0)
        after_for, after_against = _pick(after, team, g), _pick(after, opp, g)
        before_for, before_against = _pick(before, team, g), _pick(before, opp, g)
        points = after_for - before_for if None not in (after_for, before_for) else None
        against = after_against - before_against if None not in (after_against, before_against) else None
        epa = [p["epa"] for p in scrim if p["epa"] is not None]
        out.append(
            {
                "drive": d,
                "posteam": team,
                "qtr": first["qtr"],
                "start_seconds": first["game_seconds_remaining"],
                "start_yardline_100": start,
                "plays": len(scrim),
                "yards": sum(p["yards_gained"] or 0 for p in scrim),
                "epa": sum(epa) if epa else None,
                "result": first["fixed_drive_result"],
                "points": points,
                "points_against": against,
                "first_play_id": first["play_id"],
                "last_play_id": last["play_id"],
            }
        )
    return out


def win_prob(rows: list[dict], g: dict) -> list[dict]:
    """nflverse `wp` is the offense's; flip it to the home team's so the line reads one way all game, and close with
    the final result when the game is over."""
    out = []
    for r in rows:
        if r["wp"] is None or r["posteam"] is None or r["game_seconds_remaining"] is None:
            continue
        home = r["posteam"] == g["home_team"]
        out.append(
            {
                "play_id": r["play_id"],
                "qtr": r["qtr"],
                "game_seconds_remaining": r["game_seconds_remaining"],
                "home_wp": r["wp"] if home else 1 - r["wp"],
            }
        )
    if out and g["result"] is not None:
        out.append(
            {
                "play_id": None,
                "qtr": out[-1]["qtr"],
                "game_seconds_remaining": 0,
                "home_wp": 1.0 if g["result"] > 0 else (0.0 if g["result"] < 0 else 0.5),
            }
        )
    return out


def game_down_distance(conn: Connection, g: dict, team: str) -> list[dict]:
    """The team's success by down × distance in this game against the league's season-to-date rate."""
    return down_distance(conn, g["season"], team, game_id=g["game_id"])


def focus_team(g: dict, team: str) -> str:
    """The configured team when it played, else the home team (every game is browsable)."""
    return team if team in (g["home_team"], g["away_team"]) else g["home_team"]


def neighbours(conn: Connection, g: dict, team: str) -> dict:
    """The team's previous and next played games in the season, for the header's arrows."""
    stmt = (
        select(G.c.game_id, G.c.week, G.c.home_team, G.c.away_team)
        .where(and_(G.c.season == g["season"], G.c.result.is_not(None)))
        .where((G.c.home_team == team) | (G.c.away_team == team))
        .order_by(G.c.week, G.c.gameday)
    )
    ids = [r.game_id for r in conn.execute(stmt)]
    if g["game_id"] not in ids:
        return {"prev_game_id": None, "next_game_id": None}
    i = ids.index(g["game_id"])
    return {"prev_game_id": ids[i - 1] if i > 0 else None, "next_game_id": ids[i + 1] if i + 1 < len(ids) else None}
