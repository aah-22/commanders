"""Train and register the GM models.

    python -m models.train --all            # both models
    python -m models.train --model production-next

Hold-out by season: the latest target season is validation, everything earlier is training. The candidate is refit on
all seasons, logged and registered; it becomes `champion` only if its validation MAE beats both the current
champion's (read from that run's metrics) and the naive baseline's. Without MLflow the job still trains and reports,
so the gate can be rehearsed locally with --no-mlflow."""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import UTC, datetime

import pandas as pd
from sklearn.metrics import mean_absolute_error

from ingest.lineage import Tracker
from models import common, features
from models.common import ALIAS, TRUSTED

log = logging.getLogger("models.train")
MIN_EXAMPLES = 40


def fit_and_validate(name: str, ex: pd.DataFrame) -> dict:
    spec = features.SPECS[name]
    feats = spec["features"]
    seasons = sorted(ex["season"].unique())
    if len(ex) < MIN_EXAMPLES or len(seasons) < 2:
        raise ValueError(f"{name}: {len(ex)} examples over {len(seasons)} seasons is not enough to hold out a season")
    val_season = seasons[-1]
    train, val = ex[ex["season"] < val_season], ex[ex["season"] == val_season]
    numeric = [f for f in feats if f not in features.CATEGORICAL]
    model = common.make_pipeline(features.CATEGORICAL, numeric).fit(train[feats], train["target"])
    val_mae = mean_absolute_error(val["target"], model.predict(val[feats]).clip(0, 1))
    baseline_mae = mean_absolute_error(val["target"], val[spec["baseline"]].fillna(val["target"].mean()))
    final = common.make_pipeline(features.CATEGORICAL, numeric).fit(ex[feats], ex["target"])
    return {
        "model": final,
        "features": feats,
        "metrics": {
            "val_mae": float(val_mae),
            "baseline_mae": float(baseline_mae),
            "n_train": int(len(train)),
            "n_val": int(len(val)),
            "n_seasons": len(seasons),
        },
        "val_season": int(val_season),
        "example": ex[feats].head(3),
    }


def register(tr: Tracker, name: str, fitted: dict) -> dict:
    """Log the run and model; promote to champion when the gate passes. Returns what happened."""
    import mlflow.sklearn

    m = fitted["metrics"]
    tr.params({"model": name, "features": fitted["features"], "val_season": fitted["val_season"], **common.PARAMS})
    tr.metrics(m)
    info = mlflow.sklearn.log_model(
        fitted["model"],
        name="model",
        registered_model_name=name,
        input_example=fitted["example"],
        skops_trusted_types=TRUSTED,
    )
    version = str(info.registered_model_version)
    current = common.champion_metric(tr, name, "val_mae")
    beats_champion = current is None or m["val_mae"] < current
    beats_baseline = m["val_mae"] < m["baseline_mae"]
    promoted = beats_champion and beats_baseline
    if promoted:
        tr.mlflow.MlflowClient().set_registered_model_alias(name, ALIAS, version)
    tr.params({"promoted": promoted, "champion_val_mae": current})
    log.info(
        "%s v%s val_mae=%.4f baseline=%.4f champion=%s → %s",
        name,
        version,
        m["val_mae"],
        m["baseline_mae"],
        f"{current:.4f}" if current is not None else "none",
        "promoted" if promoted else "kept the champion",
    )
    return {"version": version, "promoted": promoted, "champion_val_mae": current, **m}


def train_one(tr: Tracker, name: str, frame: pd.DataFrame) -> dict:
    ex = features.SPECS[name]["examples"](frame)
    fitted = fit_and_validate(name, ex)
    with tr.run(f"train-{name}-{datetime.now(UTC):%Y%m%d}", {"stage": "train", "model": name}):
        if tr.mlflow:
            return register(tr, name, fitted)
        log.info(
            "%s (no MLflow) val_mae=%.4f baseline=%.4f",
            name,
            fitted["metrics"]["val_mae"],
            fitted["metrics"]["baseline_mae"],
        )
        return {"version": None, "promoted": False, **fitted["metrics"]}


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description="train the GM models")
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--all", action="store_true")
    which.add_argument("--model", choices=sorted(features.SPECS))
    ap.add_argument("--no-mlflow", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s %(message)s")
    names = sorted(features.SPECS) if a.all else [a.model]
    tr = Tracker(not a.no_mlflow)
    eng = common.engine()
    job = common.start_job(eng, "train", common.season())
    t0, status, out = time.time(), "ok", {}
    try:
        with eng.connect() as conn:
            frame = features.production_frame(conn)
        for name in names:
            try:
                out[name] = train_one(tr, name, frame)
            except ValueError as exc:
                log.warning("%s skipped: %s", name, exc)
                out[name] = {"skipped": str(exc)}
    except Exception as exc:
        status, out["error"] = "failed", str(exc)[:500]
        raise
    finally:
        common.finish_job(
            eng, job, status, None, len(frame) if "frame" in locals() else 0, {**out, "seconds": time.time() - t0}
        )
    return out


if __name__ == "__main__":
    main()
