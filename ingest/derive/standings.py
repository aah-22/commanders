"""gm.standings: cumulative regular-season record per team per week (bye weeks carried forward), with division and
conference ranks by win % → point differential → points for. That is a deliberate simplification of the NFL
tie-breakers (no head-to-head or common-games steps); the site says so where it shows a rank."""

from __future__ import annotations

import polars as pl
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive.io import frame
from ingest.derive.team_game_summary import team_games
from ingest.upsert import upsert

EXP = 2.37  # Pythagorean exponent for NFL points


def build(games: pl.DataFrame, teams: pl.DataFrame, season: int) -> pl.DataFrame:
    tg = team_games(games.filter(pl.col("game_type") == "REG"))
    if tg.is_empty():
        return pl.DataFrame()
    per_game = tg.select(
        "week",
        "team",
        w=(pl.col("result") == "W").cast(pl.Int64),
        l=(pl.col("result") == "L").cast(pl.Int64),
        t=(pl.col("result") == "T").cast(pl.Int64),
        pf=pl.col("points_for"),
        pa=pl.col("points_against"),
    )
    weeks = pl.DataFrame({"week": range(1, int(per_game["week"].max()) + 1)})
    active = (
        tg.select("team")
        .unique()
        .join(teams.select(team="team_abbr", conf="team_conf", division="team_division"), on="team", how="left")
    )
    grid = active.join(weeks, how="cross").join(per_game, on=["team", "week"], how="left").sort(["team", "week"])
    cum = grid.with_columns(
        [pl.col(c).fill_null(0).cum_sum().over("team").alias(c) for c in ("w", "l", "t", "pf", "pa")]
    ).rename({"w": "wins", "l": "losses", "t": "ties"})
    cum = cum.with_columns(
        games_played=pl.col("wins") + pl.col("losses") + pl.col("ties"),
        point_diff=pl.col("pf") - pl.col("pa"),
        season=pl.lit(season, dtype=pl.Int64),
    ).with_columns(
        win_pct=pl.when(pl.col("games_played") > 0)
        .then((pl.col("wins") + 0.5 * pl.col("ties")) / pl.col("games_played"))
        .otherwise(None),
        pythag_win_pct=pl.when(pl.col("pf") + pl.col("pa") > 0)
        .then(pl.col("pf") ** EXP / (pl.col("pf") ** EXP + pl.col("pa") ** EXP))
        .otherwise(None),
    )
    ranked = cum.sort(
        ["week", "win_pct", "point_diff", "pf", "team"], descending=[False, True, True, True, False], nulls_last=True
    ).with_columns(
        div_rank=pl.int_range(1, pl.len() + 1).over(["week", "division"]),
        conf_rank=pl.int_range(1, pl.len() + 1).over(["week", "conf"]),
    )
    cols = [c.name for c in schema.standings.c]
    return ranked.select(cols).sort(["week", "team"])


def run_season(conn: Connection, season: int) -> int:
    games = frame(conn, select(schema.Game.__table__).where(schema.Game.season == season), schema.Game.__table__)
    teams = frame(conn, select(schema.teams), schema.teams)
    out = build(games, teams, season)
    t = schema.standings
    conn.execute(t.delete().where(t.c.season == season))
    return upsert(conn, t, out, ["season", "week", "team"])
