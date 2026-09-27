"""gm.acquisitions: the configured team's arrivals in a season and how they came.

A draft pick (`nfl.draft_picks`), a trade in which the team received the player (`nfl.trades`), or a free-agent
signing: an active contract with the team signed that year by a player who was not on the team's roster at the end of
the previous season. A re-signing is therefore not an arrival. The contract on the card is the player's most recently
signed one (a traded player brings his). Rebuilt per season, so only that season's arrivals are touched."""

from __future__ import annotations

import polars as pl
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive import positions as pos
from ingest.derive.io import frame
from ingest.upsert import upsert

KEY = ["season", "gsis_id"]


def _latest_contract(contracts: pl.DataFrame) -> pl.DataFrame:
    df = contracts.filter(pl.col("gsis_id").is_not_null()).sort(["gsis_id", "year_signed"])
    df = df.unique(subset=["gsis_id"], keep="last")
    return df.select(
        "gsis_id",
        contract_position=pl.col("position"),
        contract_name=pl.col("player"),
        contract_team=pl.col("team_abbr"),
        apy=pl.col("apy"),
        contract_years=pl.col("years").cast(pl.Int64, strict=False),
        guaranteed=pl.col("guaranteed"),
        year_signed=pl.col("year_signed").cast(pl.Int64, strict=False),
        is_active=pl.col("is_active"),
    )


def build(
    draft_picks: pl.DataFrame,
    trades: pl.DataFrame,
    contracts: pl.DataFrame,
    prev_roster: pl.DataFrame,
    production: pl.DataFrame,
    season: int,
    team: str,
) -> pl.DataFrame:
    ct = _latest_contract(contracts) if not contracts.is_empty() else None
    rows = []
    drafted = draft_picks.filter(
        (pl.col("team") == team) & (pl.col("season") == season) & pl.col("gsis_id").is_not_null()
    )
    for r in drafted.iter_rows(named=True):
        rows.append(
            {
                "gsis_id": r["gsis_id"],
                "how": "draft",
                "date": f"{season}-04-30",
                "from_team": None,
                "draft_round": r["round"],
                "draft_pick": r["pick"],
                "source_name": r["pfr_player_name"],
                "source_position": r["position"],
            }
        )
    traded = trades.filter(
        (pl.col("received") == team) & (pl.col("season") == season) & pl.col("gsis_id").is_not_null()
    )
    # nflverse names the player later drafted with a traded pick on the pick's row; that player is a draft arrival
    if "pick_round" in traded.columns:
        traded = traded.filter(pl.col("pick_round").is_null())
    drafted_ids = set(drafted["gsis_id"].to_list())
    traded = traded.filter(~pl.col("gsis_id").is_in(list(drafted_ids))).unique(subset=["gsis_id"], keep="first")
    for r in traded.iter_rows(named=True):
        rows.append(
            {
                "gsis_id": r["gsis_id"],
                "how": "trade",
                "date": str(r["trade_date"])[:10] if r["trade_date"] else f"{season}-03-15",
                "from_team": r["gave"],
                "draft_round": None,
                "draft_pick": None,
                "source_name": r["pfr_name"],
                "source_position": None,
            }
        )
    seen = {r["gsis_id"] for r in rows}
    if ct is not None:
        was_here = set(prev_roster.filter(pl.col("team") == team)["gsis_id"].to_list())
        signed = ct.filter(
            (pl.col("contract_team") == team) & (pl.col("year_signed") == season) & pl.col("is_active").fill_null(False)
        )
        for r in signed.iter_rows(named=True):
            if r["gsis_id"] in seen or r["gsis_id"] in was_here:
                continue
            rows.append(
                {
                    "gsis_id": r["gsis_id"],
                    "how": "free agent",
                    "date": f"{season}-03-15",
                    "from_team": None,
                    "draft_round": None,
                    "draft_pick": None,
                    "source_name": r["contract_name"],
                    "source_position": r["contract_position"],
                }
            )
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows).with_columns(season=pl.lit(season, dtype=pl.Int64), team=pl.lit(team))
    if ct is not None:
        df = df.join(ct.drop(["contract_team", "is_active"]), on="gsis_id", how="left")
    else:
        df = df.with_columns(
            contract_position=None, contract_name=None, apy=None, contract_years=None, guaranteed=None, year_signed=None
        )
    prod = production.select(
        "gsis_id", prod_name=pl.col("name"), prod_position=pl.col("position"), prod_group=pl.col("pos_group")
    )
    df = df.join(prod, on="gsis_id", how="left")
    df = df.with_columns(
        name=pl.coalesce([pl.col("prod_name"), pl.col("contract_name"), pl.col("source_name")]),
        position=pl.coalesce([pl.col("contract_position"), pl.col("prod_position"), pl.col("source_position")]),
        pos_group=pl.coalesce([pos.group_expr("contract_position", "source_position"), pl.col("prod_group")]),
    )
    cols = [c.name for c in schema.acquisitions.c]
    ints = [c.name for c in schema.acquisitions.c if isinstance(c.type, schema.Integer)]
    out = df.select([c for c in cols if c in df.columns])
    return out.with_columns([pl.col(c).cast(pl.Int64, strict=False) for c in ints if c in out.columns]).sort(
        ["how", "apy"], descending=[False, True], nulls_last=True
    )


def run_season(conn: Connection, season: int, team: str) -> int:
    s = schema
    picks = frame(conn, select(s.draft_picks).where(s.draft_picks.c.season == season), s.draft_picks)
    trades = frame(conn, select(s.trades).where(s.trades.c.season == season), s.trades)
    contracts = frame(conn, select(s.contracts), s.contracts)
    prev = frame(
        conn,
        select(s.rosters_weekly).where(s.rosters_weekly.c.season == season - 1, s.rosters_weekly.c.team == team),
        s.rosters_weekly,
    )
    prod = frame(
        conn,
        select(s.player_season_production).where(s.player_season_production.c.season == season),
        s.player_season_production,
    )
    out = build(picks, trades, contracts, prev, prod, season, team)
    t = s.acquisitions
    conn.execute(t.delete().where(t.c.season == season, t.c.team == team))
    return upsert(conn, t, out, KEY)
