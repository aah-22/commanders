"""Read-side queries for one game: the header row, every play (with the explorer's filters), drives folded from the
plays in Python, and the win-probability trace. A game is at most ~200 rows, so the folding happens here, not in SQL."""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.engine import Connection

from api.queries.season import down_distance
from db import schema
from ingest.derive.filters import DISTANCE_BUCKETS

G = schema.Game.__table__
P = schema.plays

SCRIMMAGE = ("pass", "run")
SPECIAL = ("kickoff", "punt", "field_goal", "extra_point")
PLAY_TYPES = {"all": None, "scrimmage": SCRIMMAGE, "pass": ("pass",), "run": ("run",), "special": SPECIAL}
PLAY_COLUMNS = [
    "play_id",
    "fixed_drive",
    "qtr",
    "game_seconds_remaining",
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
    "success",
    "first_down",
    "touchdown",
    "sack",
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
    "posteam_score",
    "defteam_score",
    "total_home_score",
    "total_away_score",
    "fixed_drive_result",
]


def game(conn: Connection, game_id: str) -> dict | None:
    row = conn.execute(select(G).where(G.c.game_id == game_id)).first()
    return dict(row._mapping) if row else None


def plays(
    conn: Connection,
    game_id: str,
    *,
    posteam: str | None = None,
    down: int | None = None,
    distance: str | None = None,
    rz: bool = False,
    drive: int | None = None,
    kind: str = "all",
) -> list[dict]:
    """The game's plays in game order, narrowed by the explorer's filters (all optional)."""
    stmt = select(*[P.c[c] for c in PLAY_COLUMNS]).where(P.c.game_id == game_id)
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
    stmt = stmt.order_by(P.c.fixed_drive, P.c.play_id)
    return [dict(r._mapping) for r in conn.execute(stmt)]


def _score(row: dict, team: str, g: dict) -> int | None:
    col = "total_home_score" if team == g["home_team"] else "total_away_score"
    return row.get(col)


def drives(rows: list[dict], g: dict) -> list[dict]:
    """One row per fixed_drive. `points` is what the offense put up on the drive (the score at the next drive's first
    play, or the final score for the last drive, minus the score at this drive's first play); `points_against` catches a
    defensive score on the same drive. Play, yard and EPA counts cover pass and run plays only."""
    by_drive: dict[int, list[dict]] = {}
    for r in rows:
        if r["fixed_drive"] is not None:
            by_drive.setdefault(r["fixed_drive"], []).append(r)
    ordered = sorted(by_drive)
    out = []
    for i, d in enumerate(ordered):
        ps = sorted(by_drive[d], key=lambda r: r["play_id"])
        first, last = ps[0], ps[-1]
        team = next((p["posteam"] for p in ps if p["posteam"]), None)
        opp = g["away_team"] if team == g["home_team"] else g["home_team"]
        scrim = [p for p in ps if p["play_type"] in SCRIMMAGE]
        start = next(
            (p["yardline_100"] for p in ps if p["play_type"] != "kickoff" and p["yardline_100"] is not None), None
        )
        if i + 1 < len(ordered):
            nxt = sorted(by_drive[ordered[i + 1]], key=lambda r: r["play_id"])[0]
            after_for, after_against = _score(nxt, team, g), _score(nxt, opp, g)
        else:
            final = {"total_home_score": g["home_score"], "total_away_score": g["away_score"]}
            after_for, after_against = _score(final, team, g), _score(final, opp, g)
        before_for, before_against = _score(first, team, g), _score(first, opp, g)
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
