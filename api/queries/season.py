"""Read-side queries for the season endpoints: Core selects on gm.* and nfl.* (portable across Postgres and SQLite),
with the small league-wide aggregations done in Python on ≤ 32 × 18 rows."""

from __future__ import annotations

from statistics import median, quantiles

from sqlalchemy import Float, and_, case, cast, func, select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive.filters import DISTANCE_BUCKETS

G = schema.Game.__table__
TGS = schema.team_game_summary
ST = schema.standings
P = schema.plays

# metric → (numerator column, weight column); the aggregate is Σ(metric × weight) / Σ weight
WEIGHTED = {
    "off_epa_per_play": ("off_epa_per_play", "off_plays"),
    "off_success_rate": ("off_success_rate", "off_plays"),
    "off_explosive_rate": ("off_explosive_rate", "off_plays"),
    "off_proe": ("off_proe", "off_neutral_plays"),
    "off_pass_epa_per_play": ("off_pass_epa_per_play", "off_pass_plays"),
    "off_rush_epa_per_play": ("off_rush_epa_per_play", "off_rush_plays"),
    "off_points_per_drive": ("off_points_per_drive", "off_drives"),
    "def_epa_per_play": ("def_epa_per_play", "def_plays"),
    "def_success_rate": ("def_success_rate", "def_plays"),
    "def_explosive_rate": ("def_explosive_rate", "def_plays"),
    "def_pass_epa_per_play": ("def_pass_epa_per_play", "def_pass_plays"),
    "def_rush_epa_per_play": ("def_rush_epa_per_play", "def_rush_plays"),
    "def_points_per_drive": ("def_points_per_drive", "def_drives"),
}
HIGH_IS_GOOD = {k for k in WEIGHTED if k.startswith("off_")}


def games(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(select(G).where(G.c.season == season).order_by(G.c.week, G.c.gameday, G.c.gametime))
    return [dict(r._mapping) for r in rows]


def through_week(all_games: list[dict]) -> int | None:
    """The last week in which every game has a result (ranks compare full weeks only)."""
    reg = [g for g in all_games if g["game_type"] == "REG"]
    complete = None
    for wk in sorted({g["week"] for g in reg}):
        if all(g["result"] is not None for g in reg if g["week"] == wk):
            complete = wk
        else:
            break
    return complete


def team_weeks(conn: Connection, season: int, team: str | None = None) -> list[dict]:
    stmt = (
        select(TGS, G.c.gameday)
        .join(G, G.c.game_id == TGS.c.game_id)
        .where(TGS.c.season == season)
        .order_by(TGS.c.week, TGS.c.team)
    )
    if team:
        stmt = stmt.where(TGS.c.team == team)
    return [dict(r._mapping) for r in conn.execute(stmt)]


def standing(conn: Connection, season: int, team: str) -> dict | None:
    row = conn.execute(
        select(ST).where(and_(ST.c.season == season, ST.c.team == team)).order_by(ST.c.week.desc()).limit(1)
    ).first()
    return dict(row._mapping) if row else None


def aggregates(rows: list[dict], upto: int | None) -> list[dict]:
    """Per-team season-to-date aggregates over complete weeks, with league ranks per metric."""
    by_team: dict[str, list[dict]] = {}
    for r in rows:
        if upto is None or r["week"] <= upto:
            by_team.setdefault(r["team"], []).append(r)
    out = []
    for team, rs in sorted(by_team.items()):
        agg: dict = {"team": team, "games": len(rs), "ranks": {}}
        for metric, (num, wt) in WEIGHTED.items():
            pairs = [(r[num], r[wt]) for r in rs if r[num] is not None and r[wt]]
            w = sum(p[1] for p in pairs)
            agg[metric] = sum(p[0] * p[1] for p in pairs) / w if w else None
        out.append(agg)
    for metric in WEIGHTED:
        ranked = sorted(
            [a for a in out if a[metric] is not None], key=lambda a: a[metric], reverse=metric in HIGH_IS_GOOD
        )
        for i, a in enumerate(ranked):
            a["ranks"][metric] = i + 1
    return out


def league_weekly(rows: list[dict]) -> list[dict]:
    weeks: dict[int, list[dict]] = {}
    for r in rows:
        weeks.setdefault(r["week"], []).append(r)
    out = []
    for wk, rs in sorted(weeks.items()):
        entry = {"week": wk, "teams": len(rs)}
        for side in ("off", "def"):
            vals = sorted(r[f"{side}_epa_per_play"] for r in rs if r[f"{side}_epa_per_play"] is not None)
            if len(vals) >= 4:
                q = quantiles(vals, n=4)
                entry.update({f"{side}_epa_p25": q[0], f"{side}_epa_median": q[1], f"{side}_epa_p75": q[2]})
            elif vals:
                entry.update({f"{side}_epa_median": median(vals)})
        out.append(entry)
    return out


def next_game(all_games: list[dict], team: str) -> dict | None:
    for g in all_games:
        if g["result"] is None and team in (g["home_team"], g["away_team"]):
            home = g["home_team"] == team
            return {
                "game_id": g["game_id"],
                "week": g["week"],
                "opponent": g["away_team"] if home else g["home_team"],
                "is_home": home,
                "gameday": g["gameday"],
                "gametime": g["gametime"],
            }
    return None


def down_distance(conn: Connection, season: int, team: str) -> list[dict]:
    """Success rate by down × distance bucket, team vs league, over clean scrimmage plays on downs 1–3."""
    bucket = case(
        *[(P.c.ydstogo.between(lo, hi), name) for name, lo, hi in DISTANCE_BUCKETS],
        else_=None,
    ).label("bucket")
    is_team = case((P.c.posteam == team, 1), else_=0)
    stmt = (
        select(
            P.c.down,
            bucket,
            func.sum(is_team).label("team_n"),
            func.sum(is_team * cast(P.c.success, Float)).label("team_success"),
            func.count().label("league_n"),
            func.sum(cast(P.c.success, Float)).label("league_success"),
        )
        .where(
            P.c.season == season,
            P.c.play_type.in_(["pass", "run"]),
            P.c.epa.is_not(None),
            P.c.success.is_not(None),
            func.coalesce(P.c.aborted_play, 0) == 0,
            P.c.down.in_([1, 2, 3]),
            P.c.ydstogo >= 1,
        )
        .group_by(P.c.down, bucket)
    )
    found = {(r.down, r.bucket): r for r in conn.execute(stmt) if r.bucket}
    out = []
    for down in (1, 2, 3):
        for name, _, _ in DISTANCE_BUCKETS:
            r = found.get((down, name))
            tn, ln = (int(r.team_n or 0), int(r.league_n or 0)) if r else (0, 0)
            out.append(
                {
                    "down": down,
                    "bucket": name,
                    "team_n": tn,
                    "team_rate": (r.team_success or 0) / tn if r and tn else None,
                    "league_n": ln,
                    "league_rate": (r.league_success or 0) / ln if r and ln else None,
                }
            )
    return out


def schedule_rows(all_games: list[dict], weeks: list[dict], team: str) -> list[dict]:
    by_game = {w["game_id"]: w for w in weeks}
    out = []
    for g in all_games:
        if team not in (g["home_team"], g["away_team"]):
            continue
        home = g["home_team"] == team
        pf, pa = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
        result = None
        if g["result"] is not None:
            result = "T" if pf == pa else ("W" if pf > pa else "L")
        out.append(
            {
                "game_id": g["game_id"],
                "week": g["week"],
                "game_type": g["game_type"],
                "gameday": g["gameday"],
                "gametime": g["gametime"],
                "opponent": g["away_team"] if home else g["home_team"],
                "is_home": home,
                "points_for": pf,
                "points_against": pa,
                "result": result,
                "summary": by_game.get(g["game_id"]),
            }
        )
    return out
