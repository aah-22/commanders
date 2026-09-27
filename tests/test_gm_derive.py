"""gm.player_season_production, gm.positional_need and gm.acquisitions from tests/seed_gm.py, worked by hand."""

import polars as pl
import pytest
from sqlalchemy import create_engine, text

from db import schema
from ingest import derive
from ingest.derive import acquisitions, positions
from tests import seed, seed_gm


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    url = seed.seed(tmp_path_factory.mktemp("gm"))
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    with eng.begin() as conn:
        counts = derive.run_season(conn, 2026)
    return eng, counts


def rows(eng, sql: str, **params) -> list[dict]:
    with eng.connect() as c:
        return [dict(r) for r in c.execute(text(sql), params).mappings()]


def test_position_groups_resolve_from_the_most_precise_source():
    assert positions.to_group("LT") == "OL" and positions.to_group("rde") == "ED" and positions.to_group("SAF") == "S"
    assert positions.to_group("XX") is None
    df = pl.DataFrame({"a": ["ED", None, None], "b": ["OLB", "NB", None], "c": ["DL", "DB", "K"]})
    assert df.select(positions.group_expr("a", "b", "c"))["a"].to_list() == ["ED", "CB", "ST"]


def test_production_percentiles_rank_qualified_players_only(db):
    eng, counts = db
    assert counts["player_season_production"] == 16
    qb = {r["gsis_id"]: r for r in rows(eng, "SELECT * FROM player_season_production WHERE pos_group='QB'")}
    # Daniels: 2 games × (30 att + 1 sack + 5 carries) = 72 plays, EPA 15 → 0.2083; Hurts 70 plays, EPA 10 → 0.1429
    assert qb["00-Q1"]["production"] == pytest.approx(15 / 72) and qb["00-Q1"]["metric"] == "epa_per_play"
    assert (qb["00-Q1"]["production_pct"], qb["00-Q2"]["production_pct"]) == (1.0, 0.5)
    assert not qb["00-Q3"]["qualified"] and qb["00-Q3"]["production_pct"] is None  # 20 plays < 60
    assert qb["00-Q1"]["cpoe"] == pytest.approx(3.0) and qb["00-Q1"]["games"] == 2
    assert (qb["00-Q1"]["age"], qb["00-Q1"]["years_exp"], qb["00-Q1"]["draft_number"]) == (25.7, 2, 2)
    wr = {r["gsis_id"]: r for r in rows(eng, "SELECT * FROM player_season_production WHERE pos_group='WR'")}
    # Brown .5, McLaurin .4, Nabers .2 and Samuel .2 (tie), Williams unqualified (6 targets)
    assert [wr[g]["production_pct"] for g in ("00-W4", "00-W1", "00-W5", "00-W2")] == [1.0, 0.75, 0.375, 0.375]
    assert wr["00-W3"]["production_pct"] is None and wr["00-W3"]["production"] == pytest.approx(0.3)
    assert wr["00-W1"]["snap_share"] == pytest.approx(0.95) and wr["00-W1"]["snaps"] == 120


def test_low_is_good_metrics_are_flipped_and_cost_is_a_percentile(db):
    eng, _ = db
    cb = {r["gsis_id"]: r for r in rows(eng, "SELECT * FROM player_season_production WHERE pos_group='CB'")}
    assert cb["00-C1"]["passer_rating_allowed"] == pytest.approx(60.0) and cb["00-C1"]["targets_allowed"] == 10
    assert (cb["00-C1"]["production_pct"], cb["00-C2"]["production_pct"]) == (1.0, 0.5)
    wr = {r["gsis_id"]: r for r in rows(eng, "SELECT * FROM player_season_production WHERE pos_group='WR'")}
    assert [wr[g]["cost_pct"] for g in ("00-W1", "00-W4", "00-W2", "00-W5", "00-W3")] == pytest.approx(
        [1.0, 0.8, 0.6, 0.4, 0.2]
    )
    assert (wr["00-W2"]["years_left"], wr["00-W4"]["years_left"], wr["00-W1"]["years_left"]) == (0, 0, 1)
    ed = {r["gsis_id"]: r for r in rows(eng, "SELECT * FROM player_season_production WHERE pos_group='ED'")}
    assert ed["00-E1"]["pressure_rate"] == pytest.approx(10 / 100) and ed["00-E1"]["sacks"] == 2.0
    assert ed["00-E1"]["position"] == "ED"  # the OTC label wins over the roster's DL / DE


def test_need_score_adds_starters_expiring_and_age(db):
    eng, _ = db
    need = {r["pos_group"]: r for r in rows(eng, "SELECT * FROM positional_need WHERE team='WAS'")}
    # WR starters by snap share: McLaurin (.75), Samuel (.375), Williams (no pct): 50×(1−.5625) + 25×1/3 + 25×2/3
    assert need["WR"]["need_score"] == pytest.approx(46.9)
    assert (
        need["WR"]["starters"],
        need["WR"]["starters_expiring"],
        need["WR"]["starters_aging"],
        need["WR"]["depth"],
    ) == (3, 1, 2, 3)
    assert need["QB"]["need_score"] == 0.0 and need["QB"]["need_rank"] >= 5  # QB, CB and IDL all sit at zero
    assert need["LB"]["need_score"] == 50.0  # Wagner: best (only) LB, but expiring and 36
    assert need["OL"]["need_score"] == 25.0  # Tunsil: 32.1, past the OL mark
    assert "ST" not in need  # kickers and punters have no need score: snap share says nothing about them
    assert (
        need["WR"]["need_rank"] == 2
        and need["LB"]["need_rank"] == 1
        and need["WR"]["avg_age"] == pytest.approx((31.0 + 30.6 + 23.3) / 3, abs=0.05)
    )


def test_acquisitions_are_arrivals_not_resignings(db):
    eng, counts = db
    assert counts["acquisitions"] == 2
    acq = rows(eng, "SELECT * FROM acquisitions WHERE season=2026 ORDER BY how")
    assert [(a["gsis_id"], a["how"], a["pos_group"]) for a in acq] == [
        ("00-W3", "draft", "WR"),
        ("00-E1", "free agent", "ED"),
    ]
    assert (acq[0]["draft_round"], acq[0]["draft_pick"], acq[0]["apy"], acq[0]["contract_years"]) == (3, 71, 1.81, 4)
    assert acq[1]["apy"] == 12.65 and acq[1]["year_signed"] == 2026 and acq[1]["name"] == "Odafe Oweh"
    # Wagner and Samuel signed in 2026 but were on the 2025 roster: re-signings, not arrivals


def test_trades_count_as_arrivals_in_their_season():
    out = acquisitions.build(
        seed_gm.draft_picks_frame(),
        seed_gm.trades_frame(),
        seed_gm.contracts_frame(),
        pl.DataFrame({"team": ["WAS"], "gsis_id": ["00-Q1"]}),
        pl.DataFrame(schema={"gsis_id": pl.Utf8, "name": pl.Utf8, "position": pl.Utf8, "pos_group": pl.Utf8}),
        2025,
        "WAS",
    )
    by = {r["gsis_id"]: r for r in out.iter_rows(named=True)}
    assert by["00-W2"]["how"] == "trade" and by["00-W2"]["from_team"] == "SF" and by["00-W2"]["date"] == "2025-03-01"
    assert by["00-W2"]["apy"] == 17.5  # the contract on the card is the latest one signed
    assert (
        by["00-W1"]["how"] == "free agent" and by["00-I1"]["how"] == "free agent"
    )  # 2025 signings, not on the 2024 roster
    assert "00-Q1" not in by and "00-K1" in by


def test_gm_derive_is_idempotent(db):
    eng, first = db
    with eng.begin() as conn:
        again = derive.run_season(conn, 2026)
    assert again == first


def test_production_builds_when_a_source_has_no_rows_for_the_season():
    """PFR advanced stats start in 2018 and a fresh database may lack contracts; the first backfill died on 2016."""
    from ingest.derive import production

    empty = {
        t: pl.DataFrame(schema={c.name: pl.Utf8 for c in getattr(schema, t).c}) for t in ("pfr_def_game", "contracts")
    }
    out = production.build(
        seed_gm.player_game_stats_frame(),
        seed_gm.snap_counts_frame(),
        empty["pfr_def_game"],
        seed_gm.rosters_frame().filter(pl.col("season") == 2026),
        seed_gm.players_frame(),
        empty["contracts"],
        2026,
    )
    assert out.height == 16 and out["apy"].null_count() == 16 and out["pressures"].sum() == 0
    qb = out.filter(pl.col("gsis_id") == "00-Q1").row(0, named=True)
    assert qb["production_pct"] == 1.0 and qb["pos_group"] == "QB"  # the roster slot resolves the group without OTC
    bare = production.build(
        pl.DataFrame(schema={c.name: pl.Utf8 for c in schema.player_game_stats.c}),
        pl.DataFrame(schema={c.name: pl.Utf8 for c in schema.snap_counts.c}),
        empty["pfr_def_game"],
        pl.DataFrame(schema={c.name: pl.Utf8 for c in schema.rosters_weekly.c}),
        seed_gm.players_frame(),
        empty["contracts"],
        2016,
    )
    assert bare.is_empty()


def test_a_player_drafted_with_a_traded_pick_is_a_draft_arrival():
    """nflverse puts the drafted player's id on the traded pick's row (Sainristil, Sinnott, Hampton in 2024)."""
    pick_trade = pl.DataFrame(
        [
            {
                "trade_id": 9,
                "seq": 0,
                "season": 2026,
                "trade_date": "2026-04-24",
                "gave": "PHI",
                "received": "WAS",
                "pick_round": 3.0,
                "pfr_name": "Antonio Williams",
                "gsis_id": "00-W3",
            },
            {
                "trade_id": 9,
                "seq": 1,
                "season": 2026,
                "trade_date": "2026-04-24",
                "gave": "PHI",
                "received": "WAS",
                "pick_round": 5.0,
                "pfr_name": "Someone Else",
                "gsis_id": "00-X9",
            },
        ]
    )
    out = acquisitions.build(
        seed_gm.draft_picks_frame(),
        pick_trade,
        seed_gm.contracts_frame(),
        seed_gm.rosters_frame().filter(pl.col("season") == 2025),
        pl.DataFrame(schema={"gsis_id": pl.Utf8, "name": pl.Utf8, "position": pl.Utf8, "pos_group": pl.Utf8}),
        2026,
        "WAS",
    )
    by = {r["gsis_id"]: r["how"] for r in out.iter_rows(named=True)}
    assert by["00-W3"] == "draft" and "00-X9" not in by  # a pick row is never a player trade
