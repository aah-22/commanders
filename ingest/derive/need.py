"""gm.positional_need: a 0–100 need score per position group for the configured team, from its starters.

Starters are the group's top-N players by snap share (`positions.STARTERS`). The score is
    50 × (1 − starters' mean production percentile)      how good the starters are (0.5 when the group has no metric)
  + 25 × share of starters whose contract ends this season
  + 25 × share of starters past the group's aging mark (`positions.AGING`),
so 100 is "bad, expiring and old" and 0 is "elite, signed and young". Ranks are within the season."""

from __future__ import annotations

import polars as pl
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive import positions as pos
from ingest.derive.io import frame
from ingest.upsert import upsert

KEY = ["season", "pos_group"]


def build(production: pl.DataFrame, season: int, team: str) -> pl.DataFrame:
    mine = production.filter((pl.col("team") == team) & pl.col("pos_group").is_not_null())
    if mine.is_empty():
        return pl.DataFrame()
    rows = []
    for g in pos.GROUPS:
        grp = mine.filter(pl.col("pos_group") == g).sort("snap_share", descending=True, nulls_last=True)
        if grp.is_empty():
            continue
        starters = grp.head(pos.STARTERS[g])
        pcts = [p for p in starters["production_pct"].to_list() if p is not None]
        starter_pct = sum(pcts) / len(pcts) if pcts else None
        expiring = sum(1 for y in starters["years_left"].to_list() if y is not None and y <= 0)
        aging = sum(1 for a in starters["age"].to_list() if a is not None and a >= pos.AGING[g])
        ages = [a for a in starters["age"].to_list() if a is not None]
        left = [y for y in starters["years_left"].to_list() if y is not None]
        n = starters.height
        score = 50 * (1 - (starter_pct if starter_pct is not None else 0.5)) + 25 * expiring / n + 25 * aging / n
        rows.append(
            {
                "season": season,
                "pos_group": g,
                "team": team,
                "starters": n,
                "starter_pct": starter_pct,
                "starters_expiring": expiring,
                "starters_aging": aging,
                "avg_age": sum(ages) / len(ages) if ages else None,
                "contract_years_left": sum(left) / len(left) if left else None,
                "depth": grp.height,
                "need_score": round(score, 1),
            }
        )
    out = pl.DataFrame(rows).sort("need_score", descending=True)
    return out.with_columns(need_rank=pl.int_range(1, pl.len() + 1)).sort("pos_group")


def run_season(conn: Connection, season: int, team: str) -> int:
    t = schema.player_season_production
    prod = frame(conn, select(t).where(t.c.season == season), t)
    out = build(prod, season, team)
    n = schema.positional_need
    conn.execute(n.delete().where(n.c.season == season, n.c.team == team))
    return upsert(conn, n, out, KEY)
