"""/v1/gm/* and /v1/models over the seeded, derived SQLite season plus a few hand-written model outputs."""

from datetime import UTC, datetime

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
    url = seed.seed(tmp_path_factory.mktemp("gm-api"))
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    with eng.begin() as conn:
        derive.run_season(conn, 2026)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL_RO", url)
        mp.setenv("DATABASE_URL", url)
        get_settings.cache_clear()
        db.reset()
        cache._cache = None
        from api.main import app

        yield TestClient(app), eng
    get_settings.cache_clear()
    db.reset()
    cache._cache = None


def test_acquisitions_grade_on_cost_before_any_model_has_scored(client):
    c, _ = client
    j = c.get("/v1/gm/acquisitions").json()
    assert (j["season"], j["team"], j["since"]) == (2026, "WAS", 2025)
    cards = {k["gsis_id"]: k for k in j["cards"]}
    assert set(cards) == {"00-W3", "00-E1"}
    oweh = cards["00-E1"]
    # ED: Oweh's pressure rate .10 vs Armstrong's .06 → pct 1.0; APY 12.65 vs 15.0 → cost pct .5; gap +.5 → A
    assert oweh["how"] == "free agent" and oweh["production_pct"] == 1.0 and oweh["cost_pct"] == 0.5
    assert oweh["basis"] == "cost" and oweh["value_gap"] == pytest.approx(0.5) and oweh["grade"] == "A"
    assert oweh["metric"] == "pressure_rate" and oweh["snaps"] == 100 and oweh["current_team"] == "WAS"
    williams = cards["00-W3"]
    assert williams["how"] == "draft" and williams["draft_pick"] == 71 and williams["qualified"] is False
    assert williams["grade"] is None and williams["production"] == pytest.approx(0.3)


def test_acquisitions_use_the_value_model_once_scored(client):
    c, eng = client
    with eng.begin() as conn:
        conn.execute(
            schema.model_outputs.insert(),
            [
                {
                    "model": "acquisition-value",
                    "season": 2026,
                    "gsis_id": "00-E1",
                    "version": "3",
                    "run_id": "run-abc",
                    "value": 0.95,
                    "detail": {},
                    "scored_at": datetime.now(UTC),
                }
            ],
        )
    cache._cache = None
    oweh = next(k for k in c.get("/v1/gm/acquisitions?since=2026").json()["cards"] if k["gsis_id"] == "00-E1")
    assert oweh["basis"] == "model" and oweh["expected_pct"] == 0.95 and oweh["run_id"] == "run-abc"
    assert oweh["value_gap"] == pytest.approx(0.05) and oweh["grade"] == "C"


def test_need_lists_groups_with_their_starters(client):
    c, _ = client
    j = c.get("/v1/gm/need").json()
    groups = {g["pos_group"]: g for g in j["groups"]}
    assert j["groups"][0]["pos_group"] == "LB" and groups["WR"]["need_score"] == pytest.approx(46.9)
    names = [s["name"] for s in groups["WR"]["starter_list"]]
    assert names == ["Terry McLaurin", "Deebo Samuel", "Antonio Williams"]  # by snap share
    assert groups["WR"]["starter_list"][1]["years_left"] == 0
    assert len(groups["QB"]["starter_list"]) == 1 and groups["QB"]["starter_list"][0]["production_pct"] == 1.0


def test_targets_are_computed_live_until_the_score_job_runs(client):
    c, eng = client
    j = c.get("/v1/gm/targets").json()
    assert j["live"] is True and j["scored_at"] is None
    t = {x["gsis_id"]: x for x in j["targets"]}
    # Brown: pending FA (2024 + 3 − 1 = 2026), WR need 46.9, pct 1.0, 29.2 → score .469
    assert t["00-W4"]["reason"] == "pending free agent" and t["00-W4"]["score"] == pytest.approx(0.469)
    # Nabers: NYG are 0-2 → losing team; pct .375 → .176; Hurts: PHI 1-0-1 and a year left → not a target
    assert t["00-W5"]["reason"] == "losing team" and t["00-W5"]["score"] == pytest.approx(0.469 * 0.375)
    assert "00-Q2" not in t and not any(x["team"] == "WAS" for x in j["targets"])
    assert (
        j["targets"][0]["gsis_id"] == "00-W4" and t["00-W4"]["version"] == "formula-1" and t["00-W4"]["run_id"] is None
    )
    only = c.get("/v1/gm/targets?position=CB").json()["targets"]
    assert [x["gsis_id"] for x in only] == ["00-C2"]  # Banks: NYG, losing team, but CB need is 0 → score 0
    assert only[0]["score"] == 0
    assert c.get("/v1/gm/targets?position=XX").status_code == 422


def test_targets_prefer_the_stored_score(client):
    c, eng = client
    with eng.begin() as conn:
        conn.execute(
            schema.model_outputs.insert(),
            [
                {
                    "model": "target-rank",
                    "season": 2026,
                    "gsis_id": "00-W5",
                    "version": "formula-1",
                    "run_id": "run-score",
                    "value": 0.9,
                    "detail": {"reason": "losing team", "projected_pct": 0.8, "need_score": 46.9, "pos_group": "WR"},
                    "scored_at": datetime.now(UTC),
                }
            ],
        )
    cache._cache = None
    j = c.get("/v1/gm/targets").json()
    assert j["live"] is False and j["scored_at"] and [x["gsis_id"] for x in j["targets"]] == ["00-W5"]
    assert j["targets"][0]["projected_pct"] == 0.8 and j["targets"][0]["run_id"] == "run-score"


def test_models_inventory(client):
    c, _ = client
    j = c.get("/v1/models").json()
    assert j["experiment"] and j["tracking"].startswith("https://")
    by = {(o["model"], o["season"]): o for o in j["outputs"]}
    assert by[("acquisition-value", 2026)]["rows"] == 1 and by[("target-rank", 2026)]["run_id"] == "run-score"
    assert isinstance(j["jobs"], list)
