"""The play filters every derived metric shares, as polars expressions over the `nfl.plays` columns.

`play_type` is the base filter, not the `pass` / `rush` flags: the flags include penalty no-plays and exclude
scrambles, while nflverse's own team totals keep live plays with penalties and drop `no_play` rows entirely.
Kneels and spikes carry their own play_type (qb_kneel / qb_spike), so `SCRIMMAGE` already excludes them.

Two families live here. The display metrics (`CLEAN` and friends) also drop aborted snaps. The `NFLV_*` filters
reproduce nflverse's `stats_team` passing_epa / rushing_epa exactly (verified on every 2026 team-game) and exist only
so `gm.team_game_summary` can be cross-checked against `nfl.team_game_stats`: passing sums `qb_epa` over pass +
spike plays; rushing sums `epa` over run + kneel plays, aborted snaps included.
"""

from __future__ import annotations

import polars as pl

PT = pl.col("play_type")
_ABORTED = pl.col("aborted_play").fill_null(0) == 1

SCRIMMAGE = PT.is_in(["pass", "run"]) & pl.col("epa").is_not_null()
CLEAN = SCRIMMAGE & ~_ABORTED
PASS_PLAY = PT == "pass"  # sacks included; scrambles are play_type 'run'
RUSH_PLAY = PT == "run"
DROPBACK = CLEAN & (pl.col("qb_dropback") == 1)  # pass + sack + scramble
EARLY_DOWN = CLEAN & pl.col("down").is_in([1, 2])
THIRD_DOWN = CLEAN & (pl.col("down") == 3)
NEUTRAL = CLEAN & pl.col("down").is_in([1, 2, 3]) & pl.col("wp").is_between(0.1, 0.9) & pl.col("xpass").is_not_null()
EXPLOSIVE = (PASS_PLAY & (pl.col("yards_gained") >= 20)) | (RUSH_PLAY & (pl.col("yards_gained") >= 12))
RED_ZONE = CLEAN & (pl.col("yardline_100") <= 20)

NFLV_PASS = PT.is_in(["pass", "qb_spike"])
NFLV_RUSH = PT.is_in(["run", "qb_kneel"])
QB_EPA = pl.coalesce(pl.col("qb_epa"), pl.col("epa"))  # qb_epa is null on seasons ingested before phase 2

# ydstogo buckets for the down × distance view
DISTANCE_BUCKETS = [("short", 1, 3), ("mid", 4, 6), ("long", 7, 10), ("xlong", 11, 99)]


def distance_bucket() -> pl.Expr:
    expr = pl.lit(None, dtype=pl.Utf8)
    for name, lo, hi in reversed(DISTANCE_BUCKETS):
        expr = pl.when(pl.col("ydstogo").is_between(lo, hi)).then(pl.lit(name)).otherwise(expr)
    return expr
