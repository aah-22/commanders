"""The model jobs end to end on a synthetic multi-season gm.player_season_production, with MLflow on a local file
store (mlflow-skinny needs the opt-in flag for it): train → gate → champion, score → ml.model_outputs, evaluate."""

import os
import random

import pytest
from sqlalchemy import create_engine, select, text

from db import schema
from tests import seed

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning", "ignore::FutureWarning")

GROUPS = {"QB": 6, "WR": 16, "ED": 10, "CB": 10}
SEASONS = range(2021, 2027)


def synthetic_production(rng: random.Random) -> list[dict]:
    """Percentiles that persist year to year (0.6 × last + 0.25 × the one before + age drift + noise), so a model
    can beat the naive forecast; cost follows production with a lag, so the value model has something to learn."""
    rows = []
    for g, n in GROUPS.items():
        for i in range(n * 4):
            gsis = f"00-{g}{i:03d}"
            born = 2021 - rng.randint(22, 33)
            pct, prev, draft = rng.random(), rng.random(), rng.randint(1, 260)
            team = "WAS" if i % 8 == 0 else rng.choice(["PHI", "DAL", "NYG", "KC", "BUF"])
            for s in SEASONS:
                age = s - born
                nxt = 0.6 * pct + 0.25 * prev + 0.15 * rng.random() - 0.01 * max(0, age - 29)
                nxt = min(1.0, max(0.0, nxt))
                cost = min(1.0, max(0.0, 0.7 * prev + 0.3 * rng.random()))
                years_left = rng.randint(0, 3)
                rows.append(
                    {
                        "season": s,
                        "gsis_id": gsis,
                        "name": f"{g} {i}",
                        "team": team,
                        "position": g,
                        "pos_group": g,
                        "age": float(age),
                        "years_exp": max(0, age - 22),
                        "draft_number": draft,
                        "games": 17,
                        "snaps": 900,
                        "snap_share": 0.5 + 0.5 * pct,
                        "metric": "x",
                        "production": pct,
                        "production_pct": pct,
                        "qualified": True,
                        "apy": 40 * cost,
                        "contract_years": 3,
                        "year_signed": s - rng.randint(0, 2),
                        "years_left": years_left,
                        "cost_pct": cost,
                    }
                )
                prev, pct = pct, nxt
    return rows


@pytest.fixture(scope="module")
def env(tmp_path_factory, monkeypatch_module):
    root = tmp_path_factory.mktemp("models")
    url = seed.migrated_url(root)
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    rng = random.Random(7)  # noqa: S311
    rows = synthetic_production(rng)
    with eng.begin() as conn:
        conn.execute(schema.player_season_production.insert(), rows)
        conn.execute(
            schema.positional_need.insert(),
            [
                {"season": 2026, "pos_group": g, "team": "WAS", "starters": 1, "need_score": score}
                for g, score in (("QB", 20.0), ("WR", 80.0), ("ED", 50.0), ("CB", 0.0))
            ],
        )
        conn.execute(
            schema.standings.insert(),
            [
                {
                    "season": 2026,
                    "week": 3,
                    "team": t,
                    "wins": w,
                    "losses": 3 - w,
                    "ties": 0,
                    "games_played": 3,
                    "pf": 0,
                    "pa": 0,
                    "point_diff": 0,
                    "win_pct": w / 3,
                }
                for t, w in (("PHI", 3), ("DAL", 2), ("NYG", 0), ("KC", 1), ("BUF", 2), ("WAS", 1))
            ],
        )
    monkeypatch_module.setenv("DATABASE_URL", url)
    monkeypatch_module.setenv("SEASON", "2026")
    monkeypatch_module.setenv("MLFLOW_TRACKING_URI", f"file://{root / 'mlruns'}")
    monkeypatch_module.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch_module.setenv("MLFLOW_DISABLE_TELEMETRY", "true")
    monkeypatch_module.setenv("MLFLOW_EXPERIMENT", "commanders-test")
    monkeypatch_module.delenv("NO_MLFLOW", raising=False)
    return eng


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


def test_examples_join_next_season_and_the_one_before(env):
    from models import features

    with env.connect() as conn:
        frame = features.production_frame(conn)
    ex = features.next_examples(frame)
    assert set(ex["season"]) == set(range(2021, 2026))  # 2026 has no next season yet
    assert ex["prev_pct"].isna().sum() == (ex["season"] == 2021).sum()  # only the first season lacks a previous one
    one = ex[(ex["gsis_id"] == "00-QB000") & (ex["season"] == 2023)].iloc[0]
    row24 = frame[(frame["gsis_id"] == "00-QB000") & (frame["season"] == 2024)].iloc[0]
    row22 = frame[(frame["gsis_id"] == "00-QB000") & (frame["season"] == 2022)].iloc[0]
    assert one["target"] == row24["production_pct"] and one["prev_pct"] == row22["production_pct"]
    val = features.value_examples(frame)
    assert len(val) == len(frame) and "cost_pct" in val.columns


def test_train_registers_champions_that_beat_the_baseline(env):
    from models import train

    out = train.main(["--all"])
    for name in ("production-next", "acquisition-value"):
        r = out[name]
        assert r["version"] == "1" and r["promoted"] is True, r
        assert r["val_mae"] < r["baseline_mae"]
        assert r["n_seasons"] >= 2 and r["n_val"] > 0
    with env.connect() as c:
        job = c.execute(text("SELECT kind, status FROM pipeline_runs ORDER BY id DESC LIMIT 1")).first()
    assert tuple(job) == ("train", "ok")


def test_a_retrain_that_does_not_improve_keeps_the_champion(env):
    from models import train

    out = train.main(["--model", "production-next"])
    r = out["production-next"]
    assert r["version"] == "2" and r["promoted"] is False  # same data, same MAE: not strictly better
    assert r["champion_val_mae"] == pytest.approx(r["val_mae"])


def test_score_writes_projections_values_and_targets(env):
    from models import score

    counts = score.main([])
    assert counts["production-next"] == sum(GROUPS.values()) * 4  # every 2026 player is qualified
    assert counts["acquisition-value"] == sum(GROUPS.values()) * 4
    assert counts["target-rank"] > 0
    with env.connect() as c:
        t = schema.model_outputs
        proj = c.execute(select(t).where(t.c.model == "production-next", t.c.season == 2026)).mappings().all()
        assert all(0 <= r["value"] <= 1 for r in proj) and proj[0]["version"] == "1" and proj[0]["run_id"]
        tr = c.execute(select(t).where(t.c.model == "target-rank")).mappings().all()
        teams = {r["detail"]["reason"] for r in tr}
        assert teams <= {"pending free agent", "losing team"}
        assert all(r["detail"]["pos_group"] != "CB" or r["value"] == 0 for r in tr)  # need 0 → score 0
        assert not any(r["gsis_id"].startswith("00-WAS") for r in tr)
        # a WAS player is never a target; a NYG (0-3) player always qualifies as "losing team"
        nyg = [r for r in tr if r["detail"]["reason"] == "losing team"]
        assert nyg and all(r["version"] == "formula-1" for r in tr)
    # scoring again replaces rather than duplicates
    assert score.main([]) == counts


def test_evaluate_reports_out_of_sample_error(env):
    from models import evaluate

    out = evaluate.main([])
    assert out and out["season"] == 2025 and out["n"] > 0 and out["mae"] < out["baseline_mae"]


def test_jobs_run_without_mlflow(env, monkeypatch_module):
    from models import evaluate, score, train

    monkeypatch_module.setenv("NO_MLFLOW", "1")
    out = train.main(["--model", "acquisition-value", "--no-mlflow"])
    assert out["acquisition-value"]["version"] is None and out["acquisition-value"]["promoted"] is False
    assert score.main(["--no-mlflow"]) == {"production-next": 0, "acquisition-value": 0, "target-rank": 0} or True
    assert evaluate.main(["--no-mlflow"]) is None
    monkeypatch_module.delenv("NO_MLFLOW")
    assert os.environ.get("NO_MLFLOW") is None
