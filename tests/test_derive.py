"""gm.team_game_summary and gm.standings from the hand-built season in tests/seed.py (expected values worked by hand
from WAS_G1_PLAYS), plus an optional reconciliation against a real ingest database."""

import os

import polars as pl
import pytest
from sqlalchemy import create_engine, text

from db import schema
from ingest import derive
from tests import seed

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    url = seed.seed(tmp_path_factory.mktemp("derive"))
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    with eng.begin() as conn:
        counts = derive.run_season(conn, 2026)
    return eng, counts


def row(eng, sql: str, **params) -> dict:
    with eng.connect() as c:
        r = c.execute(text(sql), params).mappings().first()
    return dict(r) if r else {}


def test_display_metrics_follow_the_clean_filter(db):
    eng, counts = db
    assert counts == {"team_game_summary": 10, "standings": 12}  # 5 played games × 2, 6 teams × 2 weeks
    was = row(eng, "SELECT * FROM team_game_summary WHERE team='WAS' AND week=1")
    assert (was["opponent"], was["is_home"], was["result"], was["points_for"]) == ("NYG", True, "W", 27)
    assert was["off_plays"] == 7  # no kickoff, punt, no-play, kneel, spike or aborted snap
    assert was["off_epa_per_play"] == pytest.approx(-3.3 / 7)
    assert was["off_success_rate"] == pytest.approx(2 / 7)
    assert was["off_explosive_rate"] == pytest.approx(1 / 7)  # the 25-yard pass; 18 and 12 yards are not explosive
    assert (was["off_pass_plays"], was["off_rush_plays"]) == (5, 2)  # the scramble is a rush, the sack a pass
    assert was["off_pass_epa_per_play"] == pytest.approx(-0.64) and was["off_rush_epa_per_play"] == pytest.approx(-0.05)
    assert was["off_dropbacks"] == 6 and was["off_sacks"] == 1 and was["off_sack_rate"] == pytest.approx(1 / 6)
    assert was["off_early_down_plays"] == 5 and was["off_early_down_epa"] == pytest.approx(-0.46)
    assert was["off_pass_rate"] == pytest.approx(6 / 7)
    assert was["off_neutral_plays"] == 5 and was["off_proe"] == pytest.approx(0.16)  # wp .95 and 4th down excluded
    assert was["off_third_downs"] == 1 and was["off_third_down_conv"] == 0.0
    assert was["off_rz_trips"] == 1 and was["off_red_zone_td_rate"] == 1.0
    assert was["off_drives"] == 5 and was["off_avg_start_yardline"] == pytest.approx(42.6)  # kickoff row skipped
    assert was["off_points_per_drive"] == pytest.approx(5.4)
    assert (was["off_turnovers_on_downs"], was["off_turnovers"]) == (1, 3)  # + aborted-snap fumble + pass fumble


def test_nflverse_convention_totals_match_team_game_stats(db):
    eng, _ = db
    with eng.connect() as c:
        rows = c.execute(
            text(
                "SELECT s.team, s.off_nflv_pass_epa, t.passing_epa, s.off_nflv_rush_epa, t.rushing_epa "
                "FROM team_game_summary s JOIN team_game_stats t ON t.team = s.team AND t.game_id = s.game_id"
            )
        ).all()
    assert len(rows) == 2
    for _, p, p_ref, r, r_ref in rows:
        assert p == pytest.approx(p_ref, abs=1e-9) and r == pytest.approx(r_ref, abs=1e-9)


def test_defense_mirrors_the_opponents_offense(db):
    eng, _ = db
    was = row(eng, "SELECT * FROM team_game_summary WHERE team='WAS' AND week=1")
    nyg = row(eng, "SELECT * FROM team_game_summary WHERE team='NYG' AND week=1")
    assert was["def_plays"] == nyg["off_plays"] == 3
    assert was["def_epa_per_play"] == pytest.approx(nyg["off_epa_per_play"]) == pytest.approx(-0.1 / 3)
    assert was["def_points_per_drive"] == pytest.approx(20 / 2) and was["def_drives"] == 2


def test_ranks_are_among_the_teams_that_played_that_week(db):
    eng, _ = db
    with eng.connect() as c:
        wk = c.execute(
            text(
                "SELECT week, week_teams, off_epa_per_play_rank, def_epa_per_play_rank FROM team_game_summary WHERE team='WAS' ORDER BY week"
            )
        ).all()
    assert [(w, n) for w, n, _, _ in wk] == [(1, 6), (2, 4)]
    assert wk[0][2] == 6  # WAS's hand-built game is the worst offense of week 1
    assert wk[0][3] == 2  # NYG's defense, which faced that offense, allowed the least; WAS's is next
    with eng.connect() as c:
        ranks = sorted(c.execute(text("SELECT off_epa_per_play_rank FROM team_game_summary WHERE week=1")).scalars())
    assert ranks == [1, 2, 3, 4, 5, 6]


def test_standings_cumulate_with_ties_and_byes(db):
    eng, _ = db
    with eng.connect() as c:
        was = c.execute(
            text(
                "SELECT week, wins, losses, ties, win_pct, pf, pa, point_diff, div_rank FROM standings WHERE team='WAS' ORDER BY week"
            )
        ).all()
        kc = c.execute(text("SELECT week, wins, games_played FROM standings WHERE team='KC' ORDER BY week")).all()
        phi = row(eng, "SELECT * FROM standings WHERE team='PHI' AND week=2")
    assert was == [(1, 1, 0, 0, 1.0, 27, 20, 7, 1), (2, 1, 1, 0, 0.5, 47, 57, -10, 3)]
    assert kc == [(1, 1, 1), (2, 1, 1)]  # bye week carried forward
    assert (phi["ties"], phi["win_pct"], phi["div_rank"]) == (1, 0.75, 1)
    assert 0 < phi["pythag_win_pct"] < 1


def test_derive_is_idempotent(db):
    eng, first = db
    with eng.begin() as conn:
        again = derive.run_season(conn, 2026)
    assert again == first
    with eng.connect() as c:
        assert c.execute(text("SELECT count(*) FROM team_game_summary")).scalar() == first["team_game_summary"]


def test_build_handles_a_season_with_nothing_played():
    from ingest.derive import standings, team_game_summary

    unplayed = seed.games_frame().filter(pl.col("result").is_null())
    assert team_game_summary.build(seed.plays_frame(), unplayed).is_empty()
    assert standings.build(unplayed, seed.teams_frame(), 2026).is_empty()


@pytest.mark.skipif(
    not os.path.exists(os.environ.get("REAL_PBP_DB", "")), reason="set REAL_PBP_DB to a migrated ingest db"
)
def test_reconciles_with_nflverse_on_real_data():
    """Every team-game's nflverse-convention totals match nfl.team_game_stats (needs plays ingested with qb_epa)."""
    eng = create_engine(f"sqlite:///{os.environ['REAL_PBP_DB']}").execution_options(**schema.sqlite_options())
    with eng.begin() as conn:
        derive.run_season(conn, 2026)
        rows = conn.execute(
            text(
                "SELECT s.team, s.game_id, s.off_nflv_pass_epa - t.passing_epa, s.off_nflv_rush_epa - t.rushing_epa "
                "FROM team_game_summary s JOIN team_game_stats t ON t.team = s.team AND t.game_id = s.game_id"
            )
        ).all()
    assert rows, "no team_game_stats rows to compare"
    bad = [r for r in rows if abs(r[2]) > 0.01 or abs(r[3]) > 0.01]
    assert not bad, bad[:5]
