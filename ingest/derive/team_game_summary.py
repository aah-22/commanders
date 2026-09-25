"""gm.team_game_summary: one row per team-game with offence (`off_`) and defence (`def_`, i.e. allowed) metrics and
the team's rank among the teams that played that week. Pure polars on the `nfl.plays` / `nfl.games` frames; every
rate keeps its denominator so the API can re-aggregate exactly, and is null when that denominator is zero."""

from __future__ import annotations

import polars as pl
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive import filters as f
from ingest.derive.io import frame
from ingest.upsert import upsert

KEY = ["game_id", "team"]


def _rate(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    return pl.when(den > 0).then(num / den).otherwise(None)


def _mean(col: str, where: pl.Expr) -> pl.Expr:
    return pl.col(col).filter(where).mean()


def side(plays: pl.DataFrame, col: str) -> pl.DataFrame:
    """Metrics for the team named in `col` ('posteam' → offence, 'defteam' → defence) per game, unprefixed."""
    df = plays.filter(pl.col(col).is_not_null()).rename({col: "team"})
    agg = df.group_by(KEY).agg(
        plays=f.CLEAN.sum(),
        epa_per_play=_mean("epa", f.CLEAN),
        success_rate=_mean("success", f.CLEAN),
        explosive=(f.CLEAN & f.EXPLOSIVE).sum(),
        pass_plays=(f.CLEAN & f.PASS_PLAY).sum(),
        pass_epa_per_play=_mean("epa", f.CLEAN & f.PASS_PLAY),
        rush_plays=(f.CLEAN & f.RUSH_PLAY).sum(),
        rush_epa_per_play=_mean("epa", f.CLEAN & f.RUSH_PLAY),
        dropbacks=f.DROPBACK.sum(),
        dropback_success=_mean("success", f.DROPBACK),
        early_down_plays=f.EARLY_DOWN.sum(),
        early_down_epa=_mean("epa", f.EARLY_DOWN),
        pass_rate=_mean("qb_dropback", f.CLEAN),
        neutral_plays=f.NEUTRAL.sum(),
        proe=(pl.col("qb_dropback") - pl.col("xpass")).filter(f.NEUTRAL).mean(),
        third_downs=f.THIRD_DOWN.sum(),
        third_down_conv=_mean("first_down", f.THIRD_DOWN),
        sacks=pl.col("sack").fill_null(0).filter(f.CLEAN).sum(),
        giveaways=(pl.col("interception").fill_null(0) + pl.col("fumble_lost").fill_null(0)).filter(f.SCRIMMAGE).sum(),
        nflv_pass_epa=f.QB_EPA.filter(f.NFLV_PASS).sum(),
        nflv_rush_epa=pl.col("epa").filter(f.NFLV_RUSH).sum(),
    )
    rz = (
        df.filter(f.RED_ZONE)
        .group_by([*KEY, "fixed_drive"])
        .agg(td=(pl.col("fixed_drive_result") == "Touchdown").any())
        .group_by(KEY)
        .agg(rz_trips=pl.len(), red_zone_td_rate=pl.col("td").mean())
    )
    drives = (
        df.filter(pl.col("fixed_drive").is_not_null())
        .sort([*KEY, "fixed_drive", "play_id"])
        .group_by([*KEY, "fixed_drive"])
        .agg(
            start=pl.col("yardline_100").filter((f.PT != "kickoff") & pl.col("yardline_100").is_not_null()).first(),
            tod=(pl.col("fixed_drive_result") == "Turnover on downs").any(),
        )
        .group_by(KEY)
        .agg(drives=pl.len(), avg_start_yardline=pl.col("start").mean(), turnovers_on_downs=pl.col("tod").sum())
    )
    out = agg.join(rz, on=KEY, how="left").join(drives, on=KEY, how="left")
    return out.with_columns(
        explosive_rate=_rate(pl.col("explosive"), pl.col("plays")),
        sack_rate=_rate(pl.col("sacks"), pl.col("dropbacks")),
        rz_trips=pl.col("rz_trips").fill_null(0),
        drives=pl.col("drives").fill_null(0),
        turnovers_on_downs=pl.col("turnovers_on_downs").fill_null(0),
    ).with_columns(turnovers=pl.col("giveaways") + pl.col("turnovers_on_downs"))


def team_games(games: pl.DataFrame) -> pl.DataFrame:
    """Played games exploded to two rows (home and away perspective)."""
    played = games.filter(pl.col("result").is_not_null())
    common = ["season", "week", "game_id", "game_type"]
    home = played.select(
        *common,
        team=pl.col("home_team"),
        opponent=pl.col("away_team"),
        is_home=pl.lit(True),
        points_for=pl.col("home_score"),
        points_against=pl.col("away_score"),
    )
    away = played.select(
        *common,
        team=pl.col("away_team"),
        opponent=pl.col("home_team"),
        is_home=pl.lit(False),
        points_for=pl.col("away_score"),
        points_against=pl.col("home_score"),
    )
    both = pl.concat([home, away])
    margin = pl.col("points_for") - pl.col("points_against")
    return both.with_columns(
        result=pl.when(margin > 0).then(pl.lit("W")).when(margin < 0).then(pl.lit("L")).otherwise(pl.lit("T"))
    )


def week_ranks(df: pl.DataFrame) -> pl.DataFrame:
    """Rank among the teams with a row that week; offence high-is-good, defence low-is-good (EPA allowed)."""
    exprs = [pl.len().over(["season", "week"]).alias("week_teams")]
    for prefix, metrics in schema.RANKED.items():
        for m in metrics:
            col = f"{prefix}_{m}"
            exprs.append(
                pl.col(col).rank("min", descending=prefix == "off").over(["season", "week"]).alias(f"{col}_rank")
            )
    return df.with_columns(exprs)


def build(plays: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    tg = team_games(games)
    if tg.is_empty() or plays.is_empty():
        return pl.DataFrame()
    off = side(plays, "posteam").rename(lambda c: c if c in KEY else f"off_{c}")
    de = side(plays, "defteam").rename(lambda c: c if c in KEY else f"def_{c}")
    out = tg.join(off, on=KEY, how="inner").join(de, on=KEY, how="left")
    out = out.filter(pl.col("off_plays") > 0).with_columns(
        off_points_per_drive=_rate(pl.col("points_for"), pl.col("off_drives")),
        def_points_per_drive=_rate(pl.col("points_against"), pl.col("def_drives")),
    )
    out = week_ranks(out)
    cols = [c.name for c in schema.team_game_summary.c]
    ints = [c.name for c in schema.team_game_summary.c if isinstance(c.type, schema.Integer)]
    return out.select([c for c in cols if c in out.columns]).with_columns(
        [pl.col(c).cast(pl.Int64, strict=False) for c in ints if c in out.columns]
    )


def run_season(conn: Connection, season: int) -> int:
    """Rebuild the season from nfl.plays + nfl.games (delete then upsert, inside the caller's transaction)."""
    plays = frame(conn, select(schema.plays).where(schema.plays.c.season == season), schema.plays)
    games = frame(conn, select(schema.Game.__table__).where(schema.Game.season == season), schema.Game.__table__)
    out = build(plays, games)
    t = schema.team_game_summary
    conn.execute(t.delete().where(t.c.season == season))
    return upsert(conn, t, out, ["season", "week", "team"])
