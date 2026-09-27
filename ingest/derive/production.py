"""gm.player_season_production: one row per player with any stats, snaps or roster spot in the season.

Season-to-date totals from `nfl.player_game_stats`, snaps from `nfl.snap_counts`, pass-rush and coverage from
`nfl.pfr_def_game`, identity / age / draft slot from the latest weekly roster row (falling back to `nfl.players`),
the active contract from `nfl.contracts`. One headline metric per position group (`positions.HEADLINE`) becomes
`production`; `production_pct` is its percentile among the group's qualified players (sample ≥ `positions.MIN_SAMPLE`,
flipped where low is good); `cost_pct` is the APY percentile among the group's contracted players. Every rate keeps
its denominator (games, snaps, the sample column) so the pages can show n."""

from __future__ import annotations

from datetime import date

import polars as pl
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive import positions as pos
from ingest.derive.io import frame
from ingest.upsert import upsert

KEY = ["season", "gsis_id"]
_SUM_STATS = [
    "attempts",
    "sacks_suffered",
    "carries",
    "targets",
    "passing_epa",
    "rushing_epa",
    "receiving_epa",
    "def_tackles_solo",
    "def_tackles_for_loss",
    "def_sacks",
    "def_pass_defended",
    "def_interceptions",
    "def_fumbles_forced",
]


def _sum(col: str) -> pl.Expr:
    return pl.col(col).fill_null(0).sum().alias(col)


def _rate(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    return pl.when(den > 0).then(num / den).otherwise(None)


def _stats(pgs: pl.DataFrame) -> pl.DataFrame:
    if pgs.is_empty():
        return pl.DataFrame(
            schema={
                "gsis_id": pl.Utf8,
                "games": pl.Int64,
                "stat_team": pl.Utf8,
                "cpoe": pl.Float64,
                **dict.fromkeys(_SUM_STATS, pl.Float64),
            }
        )
    df = pgs.rename({"player_id": "gsis_id"})
    exprs = [
        pl.col("game_id").n_unique().alias("games"),
        pl.col("team").sort_by("week").last().alias("stat_team"),
        _rate((pl.col("passing_cpoe") * pl.col("attempts")).sum(), pl.col("attempts").fill_null(0).sum()).alias("cpoe"),
        *[_sum(c) if c in df.columns else pl.lit(0.0).alias(c) for c in _SUM_STATS],
    ]
    return df.group_by("gsis_id").agg(exprs)


def _snaps(snaps: pl.DataFrame) -> pl.DataFrame:
    """Season snaps and share: the player's offense or defense snaps over every game his team played."""
    if snaps.is_empty():
        return pl.DataFrame(
            schema={"gsis_id": pl.Utf8, "snaps": pl.Int64, "snap_share": pl.Float64, "snap_team": pl.Utf8}
        )
    df = snaps.filter(pl.col("gsis_id").is_not_null())
    team_games = df.group_by("team").agg(team_games=pl.col("game_id").n_unique())
    per = df.with_columns(
        side_snaps=pl.max_horizontal(
            pl.col("offense_snaps").fill_null(0), pl.col("defense_snaps").fill_null(0), pl.col("st_snaps").fill_null(0)
        ),
        side_pct=pl.max_horizontal(
            pl.col("offense_pct").fill_null(0), pl.col("defense_pct").fill_null(0), pl.col("st_pct").fill_null(0)
        ),
    )
    out = per.group_by("gsis_id").agg(
        snaps=pl.col("side_snaps").sum().cast(pl.Int64),
        pct_sum=pl.col("side_pct").sum(),
        snap_team=pl.col("team").sort_by("week").last(),
    )
    out = out.join(team_games.rename({"team": "snap_team"}), on="snap_team", how="left")
    return out.with_columns(snap_share=_rate(pl.col("pct_sum"), pl.col("team_games"))).drop(["pct_sum", "team_games"])


def _pfr(pfr: pl.DataFrame) -> pl.DataFrame:
    if pfr.is_empty():  # PFR advanced stats start in 2018
        return pl.DataFrame(
            schema={
                "gsis_id": pl.Utf8,
                "pressures": pl.Float64,
                "pfr_sacks": pl.Float64,
                "targets_allowed": pl.Float64,
                "passer_rating_allowed": pl.Float64,
            }
        )
    df = pfr.filter(pl.col("gsis_id").is_not_null())
    tgt = pl.col("def_targets").fill_null(0)
    return df.group_by("gsis_id").agg(
        pressures=pl.col("def_pressures").fill_null(0).sum(),
        pfr_sacks=pl.col("def_sacks").fill_null(0).sum(),
        targets_allowed=tgt.sum(),
        passer_rating_allowed=_rate((pl.col("def_passer_rating_allowed").fill_null(0) * tgt).sum(), tgt.sum()),
    )


def _roster(rosters: pl.DataFrame) -> pl.DataFrame:
    """The latest weekly row per player (any team), which is where the current team and status live."""
    if rosters.is_empty():
        return pl.DataFrame(
            schema={
                "gsis_id": pl.Utf8,
                "roster_team": pl.Utf8,
                "roster_name": pl.Utf8,
                "roster_position": pl.Utf8,
                "depth_position": pl.Utf8,
                "roster_birth": pl.Utf8,
                "years_exp": pl.Float64,
                "roster_draft": pl.Float64,
                "status": pl.Utf8,
            }
        )
    return (
        rosters.sort(["gsis_id", "week"])
        .group_by("gsis_id")
        .agg(
            roster_team=pl.col("team").last(),
            roster_name=pl.col("full_name").last(),
            roster_position=pl.col("position").last(),
            depth_position=pl.col("depth_chart_position").last(),
            roster_birth=pl.col("birth_date").last(),
            years_exp=pl.col("years_exp").last(),
            roster_draft=pl.col("draft_number").last(),
            status=pl.col("status").last(),
        )
    )


def _contract(contracts: pl.DataFrame, season: int) -> pl.DataFrame:
    """One active contract per player (the most recently signed)."""
    if contracts.is_empty():
        return pl.DataFrame(
            schema={
                "gsis_id": pl.Utf8,
                "contract_position": pl.Utf8,
                "apy": pl.Float64,
                "contract_years": pl.Int64,
                "year_signed": pl.Int64,
                "guaranteed": pl.Float64,
                "years_left": pl.Int64,
            }
        )
    df = contracts.filter(pl.col("gsis_id").is_not_null() & pl.col("is_active").fill_null(False))
    df = df.sort(["gsis_id", "year_signed"]).unique(subset=["gsis_id"], keep="last")
    return df.select(
        "gsis_id",
        contract_position=pl.col("position"),
        apy=pl.col("apy"),
        contract_years=pl.col("years").cast(pl.Int64, strict=False),
        year_signed=pl.col("year_signed").cast(pl.Int64, strict=False),
        guaranteed=pl.col("guaranteed"),
    ).with_columns(years_left=(pl.col("year_signed") + pl.col("contract_years") - 1 - season).cast(pl.Int64))


def _age(birth: pl.Expr, season: int) -> pl.Expr:
    ref = date(season, 9, 1)
    return (
        (pl.lit(ref) - birth.str.slice(0, 10).str.to_date(strict=False)).dt.total_days().cast(pl.Float64) / 365.25
    ).round(1)


def _pct(value: pl.Expr, qualified: pl.Expr, higher: bool) -> pl.Expr:
    """Percentile (0, 1] among qualified rows of the group; the best qualified player is 1.0."""
    v = pl.when(qualified).then(value).otherwise(None)
    n = v.count()
    ranked = v.rank("average", descending=higher)  # rank 1 is the best
    return pl.when(v.is_not_null() & (n > 0)).then(1 - (ranked - 1) / n).otherwise(None)


def build(
    pgs: pl.DataFrame,
    snaps: pl.DataFrame,
    pfr: pl.DataFrame,
    rosters: pl.DataFrame,
    players: pl.DataFrame,
    contracts: pl.DataFrame,
    season: int,
) -> pl.DataFrame:
    stats, sn, pf, ro, ct = _stats(pgs), _snaps(snaps), _pfr(pfr), _roster(rosters), _contract(contracts, season)
    ids = pl.concat([d.select("gsis_id") for d in (stats, sn, ro)]).unique()
    if ids.is_empty():
        return pl.DataFrame()
    pl_cols = players.select(
        "gsis_id",
        players_name=pl.col("display_name"),
        players_position=pl.col("position"),
        players_birth=pl.col("birth_date"),
        players_draft=pl.col("draft_pick"),
        players_team=pl.col("latest_team"),
    )
    df = ids.join(stats, on="gsis_id", how="left").join(sn, on="gsis_id", how="left")
    df = df.join(pf, on="gsis_id", how="left").join(ro, on="gsis_id", how="left")
    df = df.join(pl_cols, on="gsis_id", how="left").join(ct, on="gsis_id", how="left")
    for c in _SUM_STATS + ["games", "pressures", "pfr_sacks", "targets_allowed"]:
        if c in df.columns:
            df = df.with_columns(pl.col(c).fill_null(0))
    df = df.with_columns(
        season=pl.lit(season, dtype=pl.Int64),
        name=pl.coalesce([pl.col("roster_name"), pl.col("players_name")]),
        team=pl.coalesce([pl.col("roster_team"), pl.col("stat_team"), pl.col("snap_team"), pl.col("players_team")]),
        position=pl.coalesce(
            [
                pl.col("contract_position"),
                pl.col("depth_position"),
                pl.col("roster_position"),
                pl.col("players_position"),
            ]
        ),
        pos_group=pos.group_expr("contract_position", "depth_position", "roster_position", "players_position"),
        age=_age(pl.coalesce([pl.col("roster_birth"), pl.col("players_birth")]), season),
        draft_number=pl.coalesce([pl.col("roster_draft"), pl.col("players_draft")]).cast(pl.Int64, strict=False),
        years_exp=pl.col("years_exp").cast(pl.Int64, strict=False),
        snaps=pl.col("snaps").fill_null(0),
        plays=pl.col("attempts") + pl.col("sacks_suffered") + pl.col("carries"),
        touches=pl.col("carries") + pl.col("targets"),
    )
    df = df.with_columns(
        epa_per_play=_rate(pl.col("passing_epa") + pl.col("rushing_epa"), pl.col("plays")),
        epa_per_touch=_rate(pl.col("rushing_epa") + pl.col("receiving_epa"), pl.col("touches")),
        epa_per_target=_rate(pl.col("receiving_epa"), pl.col("targets")),
        target_share=None,  # a weekly share; the season figure needs team targets, left for the player page
        pressure_rate=_rate(pl.col("pressures"), pl.col("snaps")),
        sacks=pl.max_horizontal(pl.col("def_sacks"), pl.col("pfr_sacks")),
        tfl=pl.col("def_tackles_for_loss"),
        play_rate=_rate(
            pl.col("def_tackles_solo")
            + pl.col("def_tackles_for_loss")
            + pl.col("def_sacks")
            + pl.col("def_pass_defended")
            + pl.col("def_interceptions")
            + pl.col("def_fumbles_forced"),
            pl.col("snaps"),
        ),
        pass_defended=pl.col("def_pass_defended"),
        interceptions=pl.col("def_interceptions"),
    )
    # headline metric, qualification and percentiles, group by group
    metric = pl.lit(None, dtype=pl.Utf8)
    production = pl.lit(None, dtype=pl.Float64)
    qualified = pl.lit(False)
    for g, (col, _) in pos.HEADLINE.items():
        sample_col, floor = pos.MIN_SAMPLE[g]
        is_g = pl.col("pos_group") == g
        metric = pl.when(is_g).then(pl.lit(col)).otherwise(metric)
        production = pl.when(is_g).then(pl.col(col)).otherwise(production)
        qualified = pl.when(is_g).then(pl.col(sample_col).fill_null(0) >= floor).otherwise(qualified)
    df = df.with_columns(metric=metric, production=production, qualified=qualified & production.is_not_null())
    pct = pl.lit(None, dtype=pl.Float64)
    for g, (_, higher) in pos.HEADLINE.items():
        pct = (
            pl.when(pl.col("pos_group") == g)
            .then(_pct(pl.col("production"), pl.col("qualified"), higher).over("pos_group"))
            .otherwise(pct)
        )
    df = df.with_columns(production_pct=pct)
    df = df.with_columns(cost_pct=_pct(pl.col("apy"), pl.col("apy").is_not_null(), True).over("pos_group"))
    cols = [c.name for c in schema.player_season_production.c]
    ints = [c.name for c in schema.player_season_production.c if isinstance(c.type, schema.Integer)]
    out = df.select([c for c in cols if c in df.columns])
    return out.with_columns([pl.col(c).cast(pl.Int64, strict=False) for c in ints if c in out.columns]).sort(
        ["pos_group", "production_pct"], descending=[False, True], nulls_last=True
    )


def run_season(conn: Connection, season: int) -> int:
    s = schema
    pgs = frame(conn, select(s.player_game_stats).where(s.player_game_stats.c.season == season), s.player_game_stats)
    snaps = frame(conn, select(s.snap_counts).where(s.snap_counts.c.season == season), s.snap_counts)
    pfr = frame(conn, select(s.pfr_def_game).where(s.pfr_def_game.c.season == season), s.pfr_def_game)
    rosters = frame(conn, select(s.rosters_weekly).where(s.rosters_weekly.c.season == season), s.rosters_weekly)
    players = frame(conn, select(s.players), s.players)
    contracts = frame(conn, select(s.contracts), s.contracts)
    out = build(pgs, snaps, pfr, rosters, players, contracts, season)
    t = s.player_season_production
    conn.execute(t.delete().where(t.c.season == season))
    return upsert(conn, t, out, KEY)
