"""Training frames from gm.player_season_production.

`production-next` learns next season's production percentile from this season's (and the one before), age, snap share,
experience and draft slot. `acquisition-value` learns the production percentile a contract's APY percentile, age and
draft pedigree usually buy at the position, so an arrival is graded on actual minus expected rather than raw cost."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from models.common import read

NEXT_FEATURES = ["pos_group", "age", "years_exp", "draft_number", "snap_share", "games", "production_pct", "prev_pct"]
VALUE_FEATURES = ["pos_group", "age", "years_exp", "draft_number", "cost_pct", "contract_years"]
CATEGORICAL = ["pos_group"]
UDFA_SLOT = 300  # undrafted players get a slot past the last pick


def production_frame(conn: Connection) -> pd.DataFrame:
    t = schema.player_season_production
    cols = [
        t.c.season,
        t.c.gsis_id,
        t.c.name,
        t.c.team,
        t.c.pos_group,
        t.c.age,
        t.c.years_exp,
        t.c.draft_number,
        t.c.snap_share,
        t.c.games,
        t.c.production_pct,
        t.c.qualified,
        t.c.apy,
        t.c.cost_pct,
        t.c.contract_years,
        t.c.years_left,
    ]
    df = read(conn, select(*cols))
    df["draft_number"] = df["draft_number"].fillna(UDFA_SLOT)
    df["pos_group"] = df["pos_group"].fillna("UNK")
    return df


def with_prev(df: pd.DataFrame) -> pd.DataFrame:
    """Add `prev_pct`, the player's production percentile the season before (NaN when he had none)."""
    prev = df[["season", "gsis_id", "production_pct"]].copy()
    prev["season"] = prev["season"] + 1
    prev = prev.rename(columns={"production_pct": "prev_pct"})
    return df.merge(prev, on=["season", "gsis_id"], how="left")


def next_examples(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (player, season) with a qualified percentile this season and next; `target` is next season's."""
    base = with_prev(df[df["qualified"].astype(bool) & df["production_pct"].notna()])
    nxt = base[["season", "gsis_id", "production_pct"]].copy()
    nxt["season"] = nxt["season"] - 1
    nxt = nxt.rename(columns={"production_pct": "target"})
    out = base.merge(nxt, on=["season", "gsis_id"], how="inner")
    return out[["season", "gsis_id", *NEXT_FEATURES, "target"]].reset_index(drop=True)


def value_examples(df: pd.DataFrame) -> pd.DataFrame:
    """Contracted, qualified player-seasons: features of the deal and the player, target = production percentile."""
    out = df[df["qualified"].astype(bool) & df["production_pct"].notna() & df["cost_pct"].notna()].copy()
    out["target"] = out["production_pct"]
    return out[["season", "gsis_id", *VALUE_FEATURES, "target"]].reset_index(drop=True)


SPECS = {
    "production-next": {
        "examples": next_examples,
        "features": NEXT_FEATURES,
        "baseline": "production_pct",  # the naive forecast: next season looks like this one
    },
    "acquisition-value": {
        "examples": value_examples,
        "features": VALUE_FEATURES,
        "baseline": "cost_pct",  # the naive grade: you get what you pay for
    },
}
