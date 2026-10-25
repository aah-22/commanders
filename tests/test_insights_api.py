"""/v1/games/{game_id}/insights and the extended /plays over the seeded season. Every expectation is worked by hand
from tests/seed.py (WAS_G1_PLAYS, NYG_G1_PLAYS, EXTRA, FTN and the generic games); the arithmetic is in the comments.

The hand-built game in game order (fixed_drive, play_id) with the quarter _clock assigns (five rows per quarter):
Q1 1 2 3 4 5 · Q2 6 20 21 22 7 · Q3 23 8 9 10 11 · Q4 12 13. WAS's clean plays are 2 3 4 5 7 12 13 (dropbacks 2 4 5 7
12 13; 5 is a scramble, 4 a sack); NYG's are 21 22 23 (dropbacks 21 23). The home score rises by 7 at play 23 (the
first play after the touchdown drive) and the notional rest of the 27–20 final lands after the last play.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from api import cache, db
from api.config import get_settings
from db import schema
from ingest import derive
from tests import seed


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    url = seed.seed(tmp_path_factory.mktemp("insights"))
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    with eng.begin() as conn:
        derive.run_season(conn, 2026)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL_RO", url)
        get_settings.cache_clear()
        db.reset()
        cache._cache = None
        from api.main import app

        yield TestClient(app)
    get_settings.cache_clear()
    db.reset()
    cache._cache = None


@pytest.fixture(scope="module")
def insights(client):
    r = client.get(f"/v1/games/{seed.G1}/insights")
    assert r.status_code == 200 and r.headers["cache-control"].startswith("public, max-age=")
    return r.json()


def by_key(items: list[dict], key: str) -> dict:
    return next(i for i in items if i["key"] == key)


def test_header_focus_and_league_window(insights):
    j = insights
    assert (j["team"], j["opponent"], j["played"], j["charted"]) == ("WAS", "NYG", True, True)
    assert (j["league_through_week"], j["league_teams"]) == (2, 6)  # week 3 is unplayed; six teams have rows
    assert [t["team"] for t in j["teams"]] == ["WAS", "NYG"]
    assert j["teams"][0]["is_home"] is True and j["teams"][0]["points"] == 27 and j["teams"][1]["points"] == 20


def test_efficiency_comes_from_the_derived_summary_with_pooled_league_and_rank(insights):
    was = insights["teams"][0]
    epa = by_key(was["efficiency"], "epa_per_play")
    assert epa["value"] == pytest.approx(-3.3 / 7) and epa["n"] == 7
    assert (epa["rank"], epa["teams"], epa["kind"], epa["better"]) == (6, 6, "epa", "high")
    # league: Σ EPA / Σ clean plays over the ten team-games through week 2: the generic games sum 1.2 × scale each
    # (scales 1.6 + 1.3 + 1.9 + 0.7 + 1.3 + 1.0 + 1.6 + 0.4 = 9.8 → 11.76) plus WAS −3.3 and NYG −0.1 over 64 + 7 + 3 plays
    assert epa["league"] == pytest.approx(8.36 / 74) and epa["league_n"] == 74
    ppd = by_key(was["efficiency"], "points_per_drive")
    assert ppd["value"] == pytest.approx(5.4) and ppd["n"] == 5 and ppd["rank"] is None and ppd["kind"] == "number"
    assert by_key(was["efficiency"], "avg_start_yardline")["better"] == "low"


def test_tendencies_follow_the_derive_filters(insights):
    t = insights["teams"][0]["tendencies"]
    assert by_key(t, "pass_rate")["value"] == pytest.approx(6 / 7) and by_key(t, "pass_rate")["n"] == 7
    # league dropbacks: 4 of 8 generic plays per team-game (32) + WAS 6 + NYG 2 = 40 of 74
    assert by_key(t, "pass_rate")["league"] == pytest.approx(40 / 74)
    proe = by_key(t, "proe")
    assert (
        proe["value"] == pytest.approx(0.16) and proe["n"] == 5 and proe["rank"] == 2
    )  # off_proe_rank: NYG's +0.23 ranks first, the generic teams' 0 behind
    # league: generic plays net to 0 (pass +0.5, run −0.5), WAS +0.8 over 5, NYG +0.5 − 0.3 + 0.5 over 3 → 1.5 / 72
    assert proe["league"] == pytest.approx(1.5 / 72) and proe["league_n"] == 72
    assert by_key(t, "early_down_pass_rate")["value"] == pytest.approx(4 / 5)  # plays 2 3 4 7 12; 3 is the only run
    assert by_key(t, "shotgun_rate")["value"] == pytest.approx(6 / 7)
    assert by_key(t, "shotgun_rate")["league"] == pytest.approx(8 / 74)  # the generic games carry no shotgun flag
    assert by_key(t, "no_huddle_rate")["value"] == pytest.approx(1 / 7)
    pa = by_key(t, "play_action_rate")
    assert pa["value"] == pytest.approx(2 / 6) and pa["n"] == 6  # plays 4 and 7 of six charted dropbacks
    assert pa["league"] == pytest.approx(3 / 8) and pa["league_n"] == 8  # + NYG's play 21 of its two
    assert by_key(t, "screen_rate")["value"] == pytest.approx(1 / 5)  # play 12 of five charted pass plays
    assert by_key(t, "screen_rate")["league"] == pytest.approx(1 / 7)
    assert by_key(t, "rpo_rate")["value"] == 0 and by_key(t, "rpo_rate")["n"] == 7
    assert by_key(t, "motion_rate")["value"] == pytest.approx(2 / 7)  # plays 2 and 7
    assert by_key(t, "motion_rate")["league"] == pytest.approx(3 / 10)
    assert by_key(t, "scramble_rate")["value"] == pytest.approx(1 / 6)
    pressured = by_key(t, "pressure_rate_taken")
    assert pressured["value"] == pytest.approx(2 / 6) and pressured["better"] == "low"  # the sack and the hit on 13
    assert pressured["league"] == pytest.approx(3 / 40)  # + NYG's hit on 21
    adot = by_key(t, "adot")
    assert adot["value"] == pytest.approx(10.5) and adot["n"] == 4 and adot["kind"] == "number"  # 18 18 5 1
    assert adot["league"] == pytest.approx(53 / 6)  # + NYG 7 and 4
    assert by_key(t, "deep_rate")["value"] == 0
    assert by_key(t, "blitz_rate_faced")["value"] == pytest.approx(2 / 6)  # plays 4 and 12
    rushers = by_key(t, "pass_rushers_faced")
    assert rushers["value"] == pytest.approx(26 / 6) and rushers["league"] == pytest.approx(35 / 8)
    assert by_key(t, "light_box_rate_faced")["value"] == pytest.approx(5 / 7)  # boxes 6 6 5 6 4 of 6 6 7 5 7 6 4
    assert by_key(t, "light_box_rate_faced")["league"] == pytest.approx(6 / 10)


def test_by_down_and_splits(insights):
    was = insights["teams"][0]
    assert [(s["key"], s["value"], s["n"]) for s in was["by_down"]] == [
        ("pass_rate_1st", pytest.approx(2 / 3), 3),
        ("pass_rate_2nd", 1.0, 2),
        ("pass_rate_3rd", 1.0, 1),
    ]
    splits = {s["key"]: s for s in was["splits"]}
    align = splits["qb_alignment"]
    assert align["n"] == 7 and align["league_n"] == 10
    assert [(p["key"], p["count"]) for p in align["parts"]] == [("under_center", 1), ("shotgun", 5), ("pistol", 1)]
    assert align["parts"][1]["share"] == pytest.approx(5 / 7) and align["parts"][1]["league_share"] == pytest.approx(
        7 / 10
    )
    assert [(p["key"], p["count"]) for p in splits["run_pass"]["parts"]] == [("dropback", 6), ("run", 1)]
    assert [(p["key"], p["count"]) for p in splits["pass_location"]["parts"]] == [
        ("left", 1),
        ("middle", 1),
        ("right", 2),
    ]
    assert (
        splits["run_location"]["n"] == 1 and splits["run_location"]["parts"][1]["count"] == 1
    )  # the scramble is not a run
    assert [(p["key"], p["count"]) for p in splits["target_depth"]["parts"]] == [
        ("behind", 0),
        ("short", 2),
        ("intermediate", 2),
        ("deep", 0),
    ]
    assert [(p["key"], p["count"]) for p in splits["box_faced"]["parts"]] == [
        ("light", 5),
        ("seven", 2),
        ("stacked", 0),
    ]
    assert splits["box_faced"]["parts"][0]["share"] == pytest.approx(5 / 7)


def test_situations(insights):
    s = insights["teams"][0]["situations"]
    assert by_key(s, "third_down_conv")["value"] == 0.0 and by_key(s, "third_down_conv")["n"] == 1
    # league third downs: two per generic team-game (i = 2 fails, i = 5 converts) → 8 of 16, plus WAS's one miss
    assert by_key(s, "third_down_conv")["league"] == pytest.approx(8 / 17)
    assert by_key(s, "fourth_down_conv")["value"] == 0.0 and by_key(s, "fourth_down_conv")["n"] == 1
    assert by_key(s, "red_zone_td_rate")["value"] == 1.0 and by_key(s, "red_zone_td_rate")["n"] == 1
    late = by_key(s, "late_down_epa")
    assert late["value"] == pytest.approx(-0.5) and late["n"] == 2  # 0.2 on 3rd & 15, −1.2 on 4th & 2
    # league: generic late downs i = 2 (0.1 × scale) and i = 5 (0.2 × scale) → 0.3 × 9.8 over 16, plus WAS's two
    assert late["league"] == pytest.approx((2.94 - 1.0) / 18)
    assert by_key(s, "sack_rate")["value"] == pytest.approx(1 / 6) and by_key(s, "sack_rate")[
        "league"
    ] == pytest.approx(1 / 40)
    to = by_key(s, "turnovers")
    assert (to["value"], to["kind"], to["better"], to["league"], to["league_n"]) == (
        3,
        "count",
        "low",
        pytest.approx(0.3),
        10,
    )


def test_defense_is_the_opponents_offense(insights):
    was, nyg = insights["teams"]
    d = was["defense"]
    epa = by_key(d, "def_epa_per_play")
    assert epa["value"] == pytest.approx(-0.1 / 3) and epa["n"] == 3 and epa["rank"] == 2 and epa["better"] == "low"
    assert by_key(d, "def_success_rate")["value"] == pytest.approx(2 / 3)
    assert (
        by_key(d, "pressure_rate")["value"] == pytest.approx(1 / 2) and by_key(d, "pressure_rate")["better"] == "high"
    )
    assert by_key(d, "blitz_rate")["value"] == pytest.approx(1 / 2)  # play 23 of NYG's two charted dropbacks
    assert by_key(d, "pass_rushers")["value"] == pytest.approx(4.5)
    assert by_key(d, "light_box_rate")["value"] == pytest.approx(1 / 3)
    assert (by_key(d, "takeaways")["value"], by_key(d, "sack_rate_made")["value"]) == (0, 0.0)
    ds = {s["key"]: s for s in was["defense_splits"]}
    assert [(p["key"], p["count"]) for p in ds["box_shown"]["parts"]] == [("light", 1), ("seven", 1), ("stacked", 1)]
    assert [(p["key"], p["count"]) for p in ds["pass_rushers_sent"]["parts"]] == [
        ("three_or_fewer", 0),
        ("four", 1),
        ("five_plus", 1),
    ]
    # the mirror image: NYG's defense faced WAS's offense
    assert by_key(nyg["defense"], "pressure_rate")["value"] == pytest.approx(2 / 6)
    assert by_key(nyg["tendencies"], "pass_rate")["value"] == pytest.approx(2 / 3)


def test_quarters_use_the_score_before_the_next_play(insights):
    was, nyg = insights["teams"]
    assert [(q["label"], q["points"], q["plays"]) for q in was["quarters"]] == [
        ("Q1", 0, 4),
        ("Q2", 7, 1),
        ("Q3", 0, 0),
        ("Q4", 20, 2),
    ]
    q1 = was["quarters"][0]
    assert q1["epa_per_play"] == pytest.approx(-0.6 / 4) and q1["success_rate"] == pytest.approx(0.25)
    assert was["quarters"][2]["epa_per_play"] is None and was["quarters"][3]["epa_per_play"] == pytest.approx(-2.1)
    assert [(q["label"], q["points"], q["plays"]) for q in nyg["quarters"]] == [
        ("Q1", 0, 0),
        ("Q2", 0, 2),
        ("Q3", 0, 1),
        ("Q4", 20, 0),
    ]


def test_scoring_rows_follow_the_score_rises(insights):
    rows = insights["scoring"]
    assert rows[0] == {
        "play_id": 7,
        "qtr": 2,
        "game_seconds_remaining": 3600 - 200 * 9,
        "team": "WAS",
        "desc": "(pass) play 7",
        "points": 7,
        "home_score": 7,
        "away_score": 0,
    }
    # the notional rest of the final lands after the last play, for both teams
    assert [(r["play_id"], r["team"], r["points"], r["home_score"], r["away_score"]) for r in rows[1:]] == [
        (13, "WAS", 20, 27, 20),
        (13, "NYG", 20, 27, 20),
    ]


def test_impact_plays_are_the_biggest_swings_from_the_home_side(insights):
    plays = insights["impact_plays"]
    assert [p["play_id"] for p in plays] == [12, 13, 7, 10, 4, 2, 22, 6, 21, 3]
    p12 = plays[0]
    assert (p12["home_wp_before"], p12["home_wp_after"], p12["drive"], p12["fourth_down"]) == (
        pytest.approx(0.95),
        pytest.approx(0.75),
        7,
        False,
    )
    nyg = next(p for p in plays if p["play_id"] == 22)  # an away offense: 1 − wp, swing flipped
    assert (nyg["home_wp_before"], nyg["home_wp_after"]) == (pytest.approx(0.5), pytest.approx(0.54))
    assert next(p for p in plays if p["play_id"] == 13)["fourth_down"] is True


def test_players_are_credited_per_involvement(insights):
    was, nyg = insights["teams"]
    assert [p["gsis_id"] for p in was["players"]] == ["00-Q1", "00-W2", "00-W3", "00-R1"]
    qb = was["players"][0]
    assert (qb["name"], qb["position"], qb["plays"], qb["as_passer"], qb["as_rusher"], qb["as_receiver"]) == (
        "Jayden Daniels",
        "QB",
        6,
        5,
        1,
        0,
    )
    assert (
        qb["epa"] == pytest.approx(-3.0)
        and qb["wpa"] == pytest.approx(-0.23)
        and qb["yards"] == 54
        and qb["big_plays"] == 4
    )
    w2 = was["players"][1]
    assert (w2["name"], w2["plays"], w2["as_receiver"], w2["yards"], w2["big_plays"]) == ("Deebo Samuel", 2, 2, 37, 1)
    assert was["players"][3] == {
        "gsis_id": "00-R1",
        "name": "Austin Ekeler",
        "position": "RB",
        "team": "WAS",
        "plays": 1,
        "as_passer": 0,
        "as_rusher": 1,
        "as_receiver": 0,
        "yards": 2,
        "epa": pytest.approx(-0.3),
        "wpa": pytest.approx(-0.02),
        "big_plays": 0,
    }  # the aborted snap is not credited
    assert [p["gsis_id"] for p in nyg["players"]] == ["00-N1", "00-W5", "00-N2"]


def test_focus_team_unplayed_game_and_validation(client):
    away = client.get(f"/v1/games/{seed.G1}/insights?team=NYG").json()
    assert away["team"] == "NYG" and away["teams"][0]["team"] == "NYG" and away["teams"][0]["is_home"] is False
    j = client.get("/v1/games/2026_03_PHI_WAS/insights").json()
    assert j["played"] is False and j["charted"] is False and j["impact_plays"] == [] and j["scoring"] == []
    assert j["teams"][0]["quarters"] == [] and j["teams"][0]["players"] == []
    assert by_key(j["teams"][0]["efficiency"], "epa_per_play")["value"] is None
    assert by_key(j["teams"][0]["tendencies"], "pass_rate")["league"] == pytest.approx(
        40 / 74
    )  # the league still fills
    assert client.get("/v1/games/not-a-game/insights").status_code == 422
    assert client.get("/v1/games/2026_09_WAS_PHI/insights").status_code == 404
    assert client.get(f"/v1/games/{seed.G1}/insights?team=x").status_code == 422


def test_plays_carry_charting_and_the_new_filters(client):
    base = f"/v1/games/{seed.G1}/plays"
    rows = {p["play_id"]: p for p in client.get(base).json()["plays"]}
    assert (rows[4]["charted"], rows[4]["qb_location"], rows[4]["n_blitzers"], rows[4]["is_play_action"]) == (
        1,
        "S",
        1,
        1,
    )
    assert (rows[8]["charted"], rows[8]["qb_location"], rows[8]["n_defense_box"]) == (0, None, None)
    assert (rows[5]["qb_scramble"], rows[13]["qb_hit"], rows[2]["passer_player_id"], rows[2]["xpass"]) == (
        1,
        1,
        "00-Q1",
        0.6,
    )
    ids = lambda q: [p["play_id"] for p in client.get(f"{base}?{q}").json()["plays"]]  # noqa: E731
    assert ids("qtr=2") == [6, 20, 21, 22, 7]
    assert ids("tag=play_action") == [4, 21, 7]  # game order: drive 1, 2, 3
    assert ids("tag=pressure") == [4, 21, 13]
    assert ids("tag=big_swing") == [7, 10, 12, 13]
    assert ids("tag=explosive") == [2] and ids("tag=scramble") == [5] and ids("tag=no_huddle") == [12]
    assert ids("tag=blitz") == [4, 23, 12] and ids("tag=light_box") == [2, 4, 5, 21, 12, 13]
    assert ids("tag=screen") == [12] and ids("tag=penalty") == [8] and ids("tag=rpo") == []
    assert ids("tag=play_action&posteam=WAS") == [4, 7]
    assert client.get(f"{base}?qtr=6").status_code == 422 and client.get(f"{base}?tag=nope").status_code == 422
