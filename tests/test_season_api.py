"""/v1/season/* over the seeded, derived SQLite season."""

import time

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
    url = seed.seed(tmp_path_factory.mktemp("api"))
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


def test_summary_has_record_weeks_ranks_and_next_game(client):
    r = client.get("/v1/season/2026/summary")
    assert r.status_code == 200 and r.headers["cache-control"].startswith("public, max-age=")
    j = r.json()
    assert (j["team"], j["through_week"], j["league_teams"]) == ("WAS", 2, 6)
    assert (j["standing"]["wins"], j["standing"]["losses"], j["standing"]["div_rank"]) == (1, 1, 3)
    assert [w["week"] for w in j["weeks"]] == [1, 2] and j["weeks"][0]["gameday"] == "2026-09-13"
    agg = j["aggregate"]
    assert agg["games"] == 2 and 1 <= agg["ranks"]["off_epa_per_play"] <= 6
    assert j["next_game"] == {
        "game_id": "2026_03_PHI_WAS",
        "week": 3,
        "opponent": "PHI",
        "is_home": True,
        "gameday": "2026-09-27",
        "gametime": "13:00",
    }
    assert [w["teams"] for w in j["league_weekly"]] == [6, 4]
    assert j["league_weekly"][0]["off_epa_median"] is not None
    cells = j["down_distance"]
    assert len(cells) == 12 and {c["bucket"] for c in cells} == {"short", "mid", "long", "xlong"}
    first_long = next(c for c in cells if c["down"] == 1 and c["bucket"] == "long")
    assert first_long["team_n"] == 6 and first_long["league_n"] > first_long["team_n"]  # 3 hand-built + 3 generic


def test_aggregate_is_plays_weighted(client):
    j = client.get("/v1/season/2026/summary").json()
    w1, w2 = j["weeks"]
    expected = (w1["off_epa_per_play"] * w1["off_plays"] + w2["off_epa_per_play"] * w2["off_plays"]) / (
        w1["off_plays"] + w2["off_plays"]
    )
    assert j["aggregate"]["off_epa_per_play"] == pytest.approx(expected)


def test_league_lists_every_team_with_ranks(client):
    j = client.get("/v1/season/2026/league").json()
    assert sorted(t["team"] for t in j["teams"]) == ["BUF", "DAL", "KC", "NYG", "PHI", "WAS"]
    assert sorted(t["ranks"]["def_epa_per_play"] for t in j["teams"]) == [1, 2, 3, 4, 5, 6]


def test_games_include_unplayed_rows_without_a_summary(client):
    j = client.get("/v1/season/2026/games").json()
    rows = j["games"]
    assert [(g["week"], g["result"], g["summary"] is None) for g in rows] == [
        (1, "W", False),
        (2, "L", False),
        (3, None, True),
    ]
    assert rows[1]["opponent"] == "DAL" and rows[1]["is_home"] is False and rows[1]["points_for"] == 20


def test_validation_and_missing_season(client):
    assert client.get("/v1/season/2026/summary?team=xx").status_code == 422
    assert client.get("/v1/season/2030/summary").status_code == 422
    assert client.get("/v1/season/2025/summary").status_code == 404
    assert client.get("/v1/season/2026/summary?team=PHI").json()["standing"]["div_rank"] == 1


def test_warm_cache_is_fast(client):
    client.get("/v1/season/2026/summary")
    t = time.perf_counter()
    client.get("/v1/season/2026/summary")
    assert time.perf_counter() - t < 0.05
