"""Loader transforms and the upsert path on SQLite, through the migrated schema (no network)."""

import os
import subprocess
import sys

import polars as pl
import pytest
from sqlalchemy import create_engine, text

from db import schema
from ingest import loaders
from ingest.upsert import upsert


@pytest.fixture
def conn(tmp_path):
    url = f"sqlite:///{tmp_path / 'i.db'}"
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": os.getcwd()}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=env, capture_output=True)  # noqa: S603
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    with eng.begin() as c:
        yield c


def test_upsert_is_idempotent_and_updates_in_place(conn):
    df = pl.DataFrame(
        {
            "game_id": ["2026_01_WAS_NYG", "2026_01_DAL_PHI"],
            "season": [2026, 2026],
            "week": [1, 1],
            "game_type": ["REG", "REG"],
            "home_team": ["NYG", "PHI"],
            "away_team": ["WAS", "DAL"],
            "home_score": [None, 20],
            "away_score": [None, 24],
            "result": [None, 4],
            "extra_col": [1, 2],
        }
    )
    assert upsert(conn, schema.MIRRORS["games"], df, ["game_id"]) == 2
    assert upsert(conn, schema.MIRRORS["games"], df, ["game_id"]) == 2  # same rows again: no error, no duplicates
    played = df.with_columns(
        pl.Series("home_score", [17, 20]), pl.Series("away_score", [21, 24]), pl.Series("result", [-4, 4])
    )
    upsert(conn, schema.MIRRORS["games"], played, ["game_id"])
    rows = conn.execute(text("SELECT game_id, home_score, result FROM games ORDER BY game_id")).all()
    assert rows == [("2026_01_DAL_PHI", 20, 4), ("2026_01_WAS_NYG", 17, -4)]


def test_plays_keep_only_the_site_columns_and_never_odds(conn):
    raw = pl.DataFrame(
        {
            "game_id": ["g1", "g1"],
            "play_id": [1.0, 2.0],
            "season": [2026, 2026],
            "week": [1, 1],
            "posteam": ["WAS", "WAS"],
            "defteam": ["NYG", "NYG"],
            "epa": [0.5, -0.2],
            "success": [1.0, 0.0],
            "down": [1.0, 2.0],
            "play_type": ["pass", "run"],
            "desc": ["a", "b"],
            "vegas_wp": [0.6, 0.6],
            "spread_line": [-3.0, -3.0],
            "total_line": [44.0, 44.0],
            "wp": [0.55, 0.58],
        }
    )
    out = loaders.plays(raw)
    assert "vegas_wp" not in out.columns and "spread_line" not in out.columns and "total_line" not in out.columns
    assert out.schema["play_id"] == pl.Int64 and out.schema["down"] == pl.Int64
    assert upsert(conn, schema.MIRRORS["plays"], out, ["game_id", "play_id"]) == 2
    assert conn.execute(text("SELECT count(*) FROM plays WHERE posteam='WAS'")).scalar() == 2


def test_contracts_flatten_and_unnest_season_history():
    raw = pl.DataFrame(
        {
            "player": ["Jayden Daniels", "Vet Guy"],
            "position": ["QB", "EDGE"],
            "team": ["Commanders", "ARI/WAS"],
            "is_active": [True, False],
            "year_signed": [2024, 2022],
            "years": [4, 3],
            "value": [37.7, 30.0],
            "apy": [9.4, 10.0],
            "guaranteed": [37.7, 20.0],
            "apy_cap_pct": [0.04, 0.05],
            "otc_id": ["1", "2"],
            "gsis_id": ["00-1", None],
            "season_history": [
                [
                    {"year": "2024", "team": "Commanders", "cap_number": 6.8, "cash_paid": 30.0},
                    {"year": "Total", "team": None, "cap_number": 37.7, "cash_paid": 37.7},
                ],
                [{"year": "2022", "team": "Cardinals", "cap_number": 8.0, "cash_paid": 8.0}],
            ],
        }
    )
    flat, seasons = loaders.contracts(raw, {"Commanders": "WAS", "Cardinals": "ARI"})
    assert flat["team_abbr"].to_list() == ["WAS", "ARI"] and "season_history" not in flat.columns
    assert seasons.select(["otc_id", "season", "cap_number"]).rows() == [
        ("1", 2024, 6.8),
        ("2", 2022, 8.0),
    ]  # no 'Total'


def test_depth_charts_thin_to_the_last_snapshot_before_each_week():
    schedule = pl.DataFrame(
        {"season": [2026] * 3, "week": [1, 1, 2], "gameday": ["2026-09-10", "2026-09-13", "2026-09-20"]}
    )
    raw = pl.DataFrame(
        {
            "dt": ["2026-09-08T12:00:00Z", "2026-09-09T12:00:00Z", "2026-09-16T12:00:00Z", "2026-09-19T09:00:00Z"],
            "team": ["WAS"] * 4,
            "player_name": ["A", "B", "B", "C"],
            "espn_id": ["1", "2", "2", "3"],
            "gsis_id": ["a", "b", "b", "c"],
            "pos_grp": ["QB"] * 4,
            "pos_name": ["Quarterback"] * 4,
            "pos_abb": ["QB"] * 4,
            "pos_slot": [1] * 4,
            "pos_rank": [1] * 4,
        }
    )
    out = loaders.depth_charts(raw, schedule, 2026)
    assert out.select(["week", "gsis_id"]).sort("week").rows() == [
        (1, "b"),
        (2, "c"),
    ]  # 09-09 for week 1, 09-19 for week 2


def test_trades_get_a_sequence_and_a_gsis_crosswalk():
    raw = pl.DataFrame(
        {
            "trade_id": [7, 7, 8],
            "season": [2026] * 3,
            "trade_date": ["2026-03-01"] * 3,
            "gave": ["SF", "WAS", "NE"],
            "received": ["WAS", "SF", "WAS"],
            "pick_season": [None, 2026.0, None],
            "pick_round": [None, 2.0, None],
            "pick_number": [None, 61.0, None],
            "conditional": [0.0] * 3,
            "pfr_id": ["SamuDe00", None, "X"],
            "pfr_name": ["Deebo", None, "X"],
        }
    )
    out = loaders.trades(raw, pl.DataFrame({"pfr_id": ["SamuDe00"], "gsis_id": ["00-0035"]}))
    assert out.select(["trade_id", "seq", "gsis_id"]).rows() == [(7, 0, "00-0035"), (7, 1, None), (8, 0, None)]


def test_team_map_and_id_map_helpers():
    t = pl.DataFrame({"team_abbr": ["WAS", "ARI"], "team_nick": ["Commanders", "Cardinals"]})
    m = loaders.team_map_from_teams(t)
    assert m["Commanders"] == "WAS" and m["Redskins"] == "WAS" and m["Cardinals"] == "ARI"
    p = pl.DataFrame({"pfr_id": ["a", None, "a"], "gsis_id": ["1", "2", "3"]})
    assert loaders.id_map_from_players(p).rows() == [("a", "3")]
