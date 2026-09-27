"""Shared plumbing for the model jobs: MLflow (through the same Tracker the ingest uses, so an unreachable server is a
one-line notice, not a failure), the champion lookup, the sklearn pipeline, and the pipeline_runs bookkeeping."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy.engine import Connection, Engine

from db import schema
from ingest.lineage import Tracker
from ingest.run import current_season, engine

log = logging.getLogger("models")

ALIAS = "champion"
# MLflow 3 serialises sklearn models with skops, which refuses tree types unless they are listed; these are our own
# artifacts on our own server, and the list is written into the model so loading needs nothing extra.
TRUSTED = ["sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "numpy.dtype"]
PARAMS = {"max_iter": 300, "learning_rate": 0.05, "max_depth": 4, "l2_regularization": 1.0, "random_state": 42}


def season() -> int:
    return int(os.environ.get("SEASON", current_season()))


def team() -> str:
    return os.environ.get("TEAM", "WAS")


def make_pipeline(categorical: list[str], numeric: list[str]) -> Pipeline:
    prep = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
            ("num", "passthrough", numeric),
        ]
    )
    return Pipeline([("prep", prep), ("gbr", HistGradientBoostingRegressor(**PARAMS))])


def champion(tr: Tracker, name: str) -> tuple[object, str, str] | None:
    """(model, version, run_id) for the registry's champion of `name`, or None when there is none / no MLflow."""
    if not tr.mlflow:
        return None
    try:
        mv = tr.mlflow.MlflowClient().get_model_version_by_alias(name, ALIAS)
    except Exception as exc:  # noqa: BLE001
        log.info("no champion for %s: %s", name, str(exc)[:120])
        return None
    import mlflow.sklearn

    return mlflow.sklearn.load_model(f"models:/{name}@{ALIAS}"), str(mv.version), mv.run_id


def champion_metric(tr: Tracker, name: str, metric: str) -> float | None:
    if not tr.mlflow:
        return None
    try:
        mv = tr.mlflow.MlflowClient().get_model_version_by_alias(name, ALIAS)
        return tr.mlflow.MlflowClient().get_run(mv.run_id).data.metrics.get(metric)
    except Exception:  # noqa: BLE001
        return None


def start_job(eng: Engine, kind: str, season_: int) -> int:
    with eng.begin() as conn:
        return conn.execute(
            schema.PipelineRun.__table__.insert()
            .values(kind=kind, status="running", season=season_)
            .returning(schema.PipelineRun.id)
        ).scalar()


def finish_job(eng: Engine, job: int, status: str, run_id: str | None, rows: int, detail: dict) -> None:
    with eng.begin() as conn:
        conn.execute(
            schema.PipelineRun.__table__.update()
            .where(schema.PipelineRun.id == job)
            .values(status=status, run_id=run_id, rows=rows, detail=detail, finished_at=datetime.now(UTC))
        )


def read(conn: Connection, stmt) -> pd.DataFrame:  # noqa: ANN001
    res = conn.execute(stmt)
    # SQLAlchemy labels are `quoted_name` objects; sklearn accepts feature names only as plain str
    return pd.DataFrame(res.all(), columns=[str(k) for k in res.keys()])


__all__ = [
    "ALIAS",
    "TRUSTED",
    "champion",
    "champion_metric",
    "engine",
    "finish_job",
    "make_pipeline",
    "read",
    "season",
    "start_job",
    "team",
]
