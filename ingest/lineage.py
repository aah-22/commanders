"""MLflow lineage for jobs, silent no-op when the tracking server is unreachable (same posture as draft-engine's
lineup Tracker): one run per invocation, `stage` tag, per-table row metrics and a `log_input` dataset per source."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

import pandas as pd

log = logging.getLogger(__name__)


class Tracker:
    def __init__(self, enabled: bool = True) -> None:
        self.mlflow = None
        if not enabled or os.environ.get("NO_MLFLOW"):
            return
        try:
            import mlflow

            from api import mlflow_auth

            mlflow_auth.ensure_registered()
            mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "https://mlflow.caabi.dev"))
            mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT", "commanders"))
            mlflow.MlflowClient().search_experiments(max_results=1)
            self.mlflow = mlflow
        except Exception as exc:  # noqa: BLE001
            log.warning("MLflow unavailable, tracking disabled: %s", str(exc)[:200])

    @contextmanager
    def run(self, name: str, tags: dict):
        if not self.mlflow:
            yield None
            return
        with self.mlflow.start_run(run_name=name, tags={k: str(v) for k, v in tags.items()}) as r:
            yield r.info.run_id

    def params(self, d: dict) -> None:
        if self.mlflow:
            self.mlflow.log_params({k: str(v)[:250] for k, v in d.items()})

    def metrics(self, d: dict) -> None:
        if self.mlflow:
            self.mlflow.log_metrics({k: float(v) for k, v in d.items() if v is not None})

    def dataset(self, name: str, source: str, summary: pd.DataFrame) -> None:
        """A small per-week/per-table summary frame stands in for the rows themselves (50k plays is not a log)."""
        if self.mlflow:
            try:
                self.mlflow.log_input(self.mlflow.data.from_pandas(summary, source=source, name=name), context="ingest")
            except Exception as exc:  # noqa: BLE001
                log.warning("dataset lineage failed for %s: %s", name, str(exc)[:200])
