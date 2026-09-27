"""/v1/games/* over the seeded SQLite season (the hand-built NYG @ WAS game: WAS drives 1, 3, 5, 7, 9; NYG 2, 4)."""

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
    url = seed.seed(tmp_path_factory.mktemp("games"))
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


def test_game_detail_folds_drives_from_the_plays(client):
    r = client.get(f"/v1/games/{seed.G1}")
    assert r.status_code == 200
    j = r.json()
    assert (j["home_team"], j["away_team"], j["home_score"], j["away_score"], j["played"]) == (
        "WAS",
        "NYG",
        27,
        20,
        True,
    )
    assert j["team"] == "WAS" and j["week"] == 1
    assert (j["prev_game_id"], j["next_game_id"]) == (None, "2026_02_WAS_DAL")
    drives = j["drives"]
    assert [(d["drive"], d["posteam"]) for d in drives] == [
        (1, "WAS"),
        (2, "NYG"),
        (3, "WAS"),
        (4, "NYG"),
        (5, "WAS"),
        (7, "WAS"),
        (9, "WAS"),
    ]
    d1 = drives[0]
    # kickoff excluded: 4 scrimmage plays (25 + 2 - 7 + 6 yards, EPA 0.5 - 0.3 - 1.0 + 0.2), punt result, first play a kickoff
    assert (d1["plays"], d1["yards"], d1["result"], d1["start_yardline_100"]) == (4, 26, "Punt", 75)
    assert d1["epa"] == pytest.approx(-0.6)
    assert d1["qtr"] == 1 and d1["start_seconds"] == 3600
    d3 = drives[2]
    assert (d3["result"], d3["points"], d3["points_against"]) == ("Touchdown", 7, 0)
    assert drives[1]["points"] == 0  # NYG punt drive
    last = drives[-1]
    assert last["points"] == 27 - 7  # the notional rest of the final score lands on the last drive
    assert (last["first_play_id"], last["last_play_id"]) == (13, 13)


def test_win_probability_is_from_the_home_side_and_closes_on_the_result(client):
    j = client.get(f"/v1/games/{seed.G1}").json()
    wp = j["win_prob"]
    assert wp[0]["home_wp"] == 0.5 and wp[0]["play_id"] == 1
    spike = next(p for p in wp if p["play_id"] == 11)
    assert spike["home_wp"] == pytest.approx(0.95)
    nyg = next(p for p in wp if p["play_id"] == 21)
    assert nyg["home_wp"] == pytest.approx(0.5)  # 1 - 0.5, offense is the away team
    assert wp[-1] == {"play_id": None, "qtr": wp[-2]["qtr"], "game_seconds_remaining": 0, "home_wp": 1.0}
    assert all(a["game_seconds_remaining"] >= b["game_seconds_remaining"] for a, b in zip(wp, wp[1:], strict=False))


def test_game_down_distance_counts_only_this_game_for_the_team(client):
    j = client.get(f"/v1/games/{seed.G1}").json()
    cells = j["down_distance"]
    assert len(cells) == 12
    first_long = next(c for c in cells if c["down"] == 1 and c["bucket"] == "long")
    assert first_long["team_n"] == 3  # plays 2, 3, 7 (1st & 10); the season view counts 6
    assert first_long["league_n"] > first_long["team_n"]
    away = client.get(f"/v1/games/{seed.G1}?team=NYG").json()
    assert away["team"] == "NYG"
    assert next(c for c in away["down_distance"] if c["down"] == 1 and c["bucket"] == "long")["team_n"] == 2


def test_focus_falls_back_to_the_home_team_when_was_did_not_play(client):
    j = client.get("/v1/games/2026_01_DAL_PHI").json()
    assert j["team"] == "PHI" and j["played"] is True and len(j["drives"]) == 2


def test_plays_filters(client):
    base = f"/v1/games/{seed.G1}/plays"
    j = client.get(base).json()
    assert j["total"] == 17 and [p["play_id"] for p in j["plays"]][:6] == [1, 2, 3, 4, 5, 6]
    assert j["plays"][1]["desc"] == "(pass) play 2" and j["plays"][1]["qtr"] == 1
    assert client.get(f"{base}?type=scrimmage").json()["total"] == 11  # 8 WAS + 3 NYG pass/run
    assert client.get(f"{base}?posteam=NYG").json()["total"] == 4
    assert client.get(f"{base}?down=3").json()["total"] == 1
    assert [p["play_id"] for p in client.get(f"{base}?distance=short").json()["plays"]] == [22, 13]  # game order
    assert [p["play_id"] for p in client.get(f"{base}?rz=true").json()["plays"]] == [7]
    assert [p["play_id"] for p in client.get(f"{base}?drive=7").json()["plays"]] == [11, 12]
    assert client.get(f"{base}?type=special").json()["total"] == 3  # two kickoffs and a punt
    assert client.get(f"{base}?type=pass&posteam=WAS&down=2").json()["total"] == 2


def test_validation_and_missing_game(client):
    assert client.get("/v1/games/not-a-game").status_code == 422
    assert client.get("/v1/games/2026_09_WAS_PHI").status_code == 404
    assert client.get(f"/v1/games/{seed.G1}/plays?down=5").status_code == 422
    assert client.get(f"/v1/games/{seed.G1}/plays?distance=huge").status_code == 422
    assert client.get(f"/v1/games/{seed.G1}/plays?type=trick").status_code == 422
    assert client.get(f"/v1/games/{seed.G1}?team=x").status_code == 422


def test_unplayed_game_has_no_drives(client):
    j = client.get("/v1/games/2026_03_PHI_WAS").json()
    assert j["played"] is False and j["drives"] == [] and j["win_prob"] == []
    assert j["prev_game_id"] is None  # not in the played list, so no arrows
