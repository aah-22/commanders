"""nflverse → normalised polars frames, one function per mirror table. Pure transforms on frames (the tests feed
synthetic frames through the same code the jobs use); the `fetch_*` wrappers are the only network calls."""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from ingest.sources import (
    GAME_COLUMNS,
    PBP_COLUMNS,
    PLAYER_COLUMNS,
    PLAYER_STAT_COLUMNS,
    TEAM_COLUMNS,
    TEAM_GAME_STAT_COLUMNS,
)

INT_PLAY_COLUMNS = [
    "play_id",
    "season",
    "week",
    "fixed_drive",
    "drive",
    "qtr",
    "down",
    "ydstogo",
    "yardline_100",
    "goal_to_go",
    "game_seconds_remaining",
    "half_seconds_remaining",
    "yards_gained",
    "pass",
    "rush",
    "qb_dropback",
    "qb_scramble",
    "qb_kneel",
    "qb_spike",
    "shotgun",
    "no_huddle",
    "sack",
    "qb_hit",
    "interception",
    "fumble_lost",
    "touchdown",
    "penalty",
    "complete_pass",
    "incomplete_pass",
    "first_down",
    "series",
    "series_success",
    "aborted_play",
    "posteam_score",
    "defteam_score",
    "score_differential",
    "total_home_score",
    "total_away_score",
]


def _keep(df: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    return df.select([c for c in columns if c in df.columns])


def _ints(df: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    return df.with_columns([pl.col(c).cast(pl.Int64, strict=False) for c in columns if c in df.columns])


def teams(df: pl.DataFrame) -> pl.DataFrame:
    return _keep(df, TEAM_COLUMNS).unique(subset=["team_abbr"], keep="last")


def players(df: pl.DataFrame) -> pl.DataFrame:
    out = _keep(df, PLAYER_COLUMNS).filter(pl.col("gsis_id").is_not_null())
    if "birth_date" in out.columns:
        out = out.with_columns(pl.col("birth_date").cast(pl.Utf8))
    return out


def games(df: pl.DataFrame) -> pl.DataFrame:
    out = _keep(df, GAME_COLUMNS)
    return _ints(
        out,
        [
            "season",
            "week",
            "away_score",
            "home_score",
            "result",
            "total",
            "overtime",
            "div_game",
            "temp",
            "wind",
            "away_rest",
            "home_rest",
        ],
    )


def plays(df: pl.DataFrame) -> pl.DataFrame:
    """The ~60 of 372 pbp columns the site uses; no vegas_wp / spread columns, by design."""
    out = _keep(df, PBP_COLUMNS).filter(pl.col("play_id").is_not_null())
    return _ints(out, INT_PLAY_COLUMNS)


def player_game_stats(df: pl.DataFrame) -> pl.DataFrame:
    out = _keep(df, PLAYER_STAT_COLUMNS).filter(pl.col("game_id").is_not_null() & pl.col("player_id").is_not_null())
    return _ints(
        out,
        [
            "season",
            "week",
            "completions",
            "attempts",
            "passing_yards",
            "passing_tds",
            "passing_interceptions",
            "sacks_suffered",
            "carries",
            "rushing_yards",
            "rushing_tds",
            "receptions",
            "targets",
            "receiving_yards",
            "receiving_tds",
        ],
    )


def team_game_stats(df: pl.DataFrame) -> pl.DataFrame:
    """nflverse team-week stats, the independent cross-check for the derived team_game_summary."""
    out = _keep(df, TEAM_GAME_STAT_COLUMNS).filter(pl.col("game_id").is_not_null() & pl.col("team").is_not_null())
    return _ints(
        out,
        [
            "season",
            "week",
            "completions",
            "attempts",
            "passing_yards",
            "passing_tds",
            "passing_interceptions",
            "sacks_suffered",
            "carries",
            "rushing_yards",
            "rushing_tds",
            "receptions",
            "targets",
            "receiving_yards",
            "receiving_tds",
            "penalties",
            "fg_made",
            "fg_att",
            "pat_made",
            "pat_att",
            "pt_att",
        ],
    )


def snap_counts(df: pl.DataFrame, id_map: pl.DataFrame) -> pl.DataFrame:
    """pfr-keyed; `gsis_id` resolved through the players crosswalk (nullable while a rookie has no pfr_id there)."""
    out = df.filter(pl.col("pfr_player_id").is_not_null() & pl.col("game_id").is_not_null())
    out = out.join(
        id_map.select(["pfr_id", "gsis_id"]).rename({"pfr_id": "pfr_player_id"}), on="pfr_player_id", how="left"
    )
    return _ints(out, ["season", "week"])


def rosters_weekly(df: pl.DataFrame) -> pl.DataFrame:
    out = df.filter(pl.col("gsis_id").is_not_null())
    if "birth_date" in out.columns:
        out = out.with_columns(pl.col("birth_date").cast(pl.Utf8))
    return _ints(out, ["season", "week"])


def depth_charts_legacy(df: pl.DataFrame, season: int) -> pl.DataFrame:
    """nflverse depth charts through 2024 are already one chart per team-week (`club_code`, `week`, `depth_team`,
    `depth_position`); map them onto the daily-snapshot layout the table follows. `pos_abb` is the depth-chart slot
    (`RG`, `LCB`), falling back to the roster position when the slot is blank; `pos_rank` is the string within the slot."""
    slot = pl.col("depth_position").str.strip_chars()
    return (
        df.filter(pl.col("week").is_not_null() & pl.col("gsis_id").is_not_null())
        .select(
            pl.lit(season).alias("season"),
            pl.col("week").cast(pl.Int64),
            pl.col("club_code").alias("team"),
            pl.col("gsis_id"),
            pl.when(slot == "").then(pl.col("position")).otherwise(slot).alias("pos_abb"),
            pl.lit(None, dtype=pl.Utf8).alias("dt"),
            pl.col("full_name").alias("player_name"),
            pl.lit(None, dtype=pl.Utf8).alias("espn_id"),
            pl.col("formation").alias("pos_grp"),
            pl.col("position").alias("pos_name"),
            pl.lit(None, dtype=pl.Int64).alias("pos_slot"),
            pl.col("depth_team").cast(pl.Int64, strict=False).alias("pos_rank"),
        )
        .unique(subset=["season", "week", "team", "gsis_id", "pos_abb"], keep="last")
    )


def depth_charts(df: pl.DataFrame, schedule: pl.DataFrame, season: int) -> pl.DataFrame:
    """Daily snapshots thinned to one per week: the last snapshot dated before each week's first kickoff, for the weeks
    already played and the one coming up (a week further out has no chart of its own yet). Seasons before 2025 come
    in the weekly legacy layout and go through `depth_charts_legacy`."""
    if df.is_empty():
        return df
    if "dt" not in df.columns:
        return depth_charts_legacy(df, season)
    weeks = (
        schedule.filter(pl.col("season") == season)
        .group_by("week")
        .agg(pl.col("gameday").min().alias("first_game"))
        .sort("week")
    )
    snaps = df.with_columns(pl.col("dt").str.slice(0, 10).alias("day"))
    days = snaps.select("day").unique().sort("day")
    horizon = (date.fromisoformat(days["day"][-1]) + timedelta(days=7)).isoformat()
    rows = []
    for wk, first in weeks.iter_rows():
        before = days.filter(pl.col("day") < str(first))
        if before.is_empty() or str(first) > horizon:
            continue
        rows.append(snaps.filter(pl.col("day") == before["day"][-1]).with_columns(pl.lit(int(wk)).alias("week")))
    if not rows:
        return df.clear().with_columns(pl.lit(0).alias("week"), pl.lit(season).alias("season"))
    out = pl.concat(rows).with_columns(pl.lit(season).alias("season"))
    return out.filter(pl.col("gsis_id").is_not_null()).unique(
        subset=["season", "week", "team", "gsis_id", "pos_abb"], keep="last"
    )


def injuries(df: pl.DataFrame) -> pl.DataFrame:
    return _ints(df.filter(pl.col("gsis_id").is_not_null()), ["season", "week"])


def contracts(df: pl.DataFrame, team_map: dict[str, str]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """OTC contracts flattened plus one row per contract-season from `season_history` ('Total' rows dropped).
    OTC writes a nickname ('Commanders') for one-team deals and abbreviations ('ARI/WAS') for traded ones; `team_abbr`
    resolves the first team either way and `team_raw` keeps the original."""
    first = pl.col("team_raw").str.split("/").list.first()
    base = (
        df.rename({"team": "team_raw"})
        .with_columns(
            pl.when(first.str.contains(r"^[A-Z]{2,3}$"))
            .then(first)
            .otherwise(first.replace_strict(team_map, default=None))
            .alias("team_abbr"),
            pl.col("year_signed").cast(pl.Int64, strict=False),
        )
        .filter(pl.col("otc_id").is_not_null() & pl.col("year_signed").is_not_null())
    )
    if "date_of_birth" in base.columns:
        base = base.with_columns(pl.col("date_of_birth").cast(pl.Utf8))
    flat = base.drop([c for c in ("season_history", "contract_history") if c in base.columns])
    seasons = pl.DataFrame()
    if "season_history" in base.columns:
        seasons = (
            base.select(["otc_id", "year_signed", "team_raw", "season_history"])
            .explode("season_history")
            .filter(pl.col("season_history").is_not_null())
            .unnest("season_history")
            .filter(pl.col("year").cast(pl.Utf8) != "Total")
            .with_columns(pl.col("year").cast(pl.Int64, strict=False).alias("season"))
            .drop("year")
            .filter(pl.col("season").is_not_null())
        )
    return flat, seasons


def draft_picks(df: pl.DataFrame) -> pl.DataFrame:
    return _ints(df.filter(pl.col("pick").is_not_null()), ["season", "round", "pick"])


def trades(df: pl.DataFrame, id_map: pl.DataFrame) -> pl.DataFrame:
    """One row per asset moved; `seq` numbers the assets within a trade (nflverse has no per-row key)."""
    out = df.with_columns(pl.int_range(pl.len()).over("trade_id").alias("seq"))
    out = out.join(id_map.select(["pfr_id", "gsis_id"]), on="pfr_id", how="left")
    return _ints(out, ["trade_id", "seq", "season"])


def pfr(df: pl.DataFrame, id_map: pl.DataFrame) -> pl.DataFrame:
    out = df.filter(pl.col("pfr_player_id").is_not_null() & pl.col("game_id").is_not_null())
    out = out.join(
        id_map.select(["pfr_id", "gsis_id"]).rename({"pfr_id": "pfr_player_id"}), on="pfr_player_id", how="left"
    )
    return _ints(out, ["season", "week"])


def ngs(df: pl.DataFrame) -> pl.DataFrame:
    return _ints(df.filter(pl.col("player_gsis_id").is_not_null()), ["season", "week"])


def id_map_from_players(p: pl.DataFrame) -> pl.DataFrame:
    """pfr_id → gsis_id crosswalk (one row per pfr_id)."""
    return p.select(["pfr_id", "gsis_id"]).filter(pl.col("pfr_id").is_not_null()).unique(subset=["pfr_id"], keep="last")


def team_map_from_teams(t: pl.DataFrame) -> dict[str, str]:
    """'Commanders' → 'WAS', with the historical nicknames OTC still uses."""
    m = dict(zip(t["team_nick"].to_list(), t["team_abbr"].to_list(), strict=True))
    m.setdefault("Redskins", "WAS")
    m.setdefault("Football Team", "WAS")
    m.setdefault("Raiders", "LV")
    m.setdefault("Chargers", "LAC")
    m.setdefault("Rams", "LA")
    return m
