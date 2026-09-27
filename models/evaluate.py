"""Evaluate the production-next champion out of sample: predict the latest completed season from the one before it
(no target leakage) and log MAE against the naive forecast.

    python -m models.evaluate
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import UTC, datetime

from sklearn.metrics import mean_absolute_error

from ingest.lineage import Tracker
from models import common, features

log = logging.getLogger("models.evaluate")


def evaluate(tr: Tracker, frame) -> dict | None:  # noqa: ANN001
    champ = common.champion(tr, "production-next")
    if champ is None:
        log.info("no production-next champion to evaluate")
        return None
    model, version, run_id = champ
    ex = features.next_examples(frame)
    if ex.empty:
        log.info("no completed season pair to evaluate")
        return None
    season = int(ex["season"].max())
    last = ex[ex["season"] == season]
    pred = model.predict(last[features.NEXT_FEATURES]).clip(0, 1)
    out = {
        "season": season,
        "n": int(len(last)),
        "mae": float(mean_absolute_error(last["target"], pred)),
        "baseline_mae": float(mean_absolute_error(last["target"], last["production_pct"])),
        "version": version,
        "champion_run_id": run_id,
    }
    log.info(
        "production-next v%s on %s→%s: mae=%.4f baseline=%.4f n=%s",
        version,
        season,
        season + 1,
        out["mae"],
        out["baseline_mae"],
        out["n"],
    )
    return out


def main(argv: list[str] | None = None) -> dict | None:
    ap = argparse.ArgumentParser(description="evaluate the champion out of sample")
    ap.add_argument("--no-mlflow", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s %(message)s")
    tr = Tracker(not a.no_mlflow)
    eng = common.engine()
    job = common.start_job(eng, "evaluate", common.season())
    status, out = "ok", None
    try:
        with eng.connect() as conn:
            frame = features.production_frame(conn)
        with tr.run(f"evaluate-{datetime.now(UTC):%Y%m%d}", {"stage": "evaluate", "model": "production-next"}):
            out = evaluate(tr, frame)
            if out:
                tr.params(
                    {"version": out["version"], "champion_run_id": out["champion_run_id"], "season": out["season"]}
                )
                tr.metrics({"mae": out["mae"], "baseline_mae": out["baseline_mae"], "n": out["n"]})
    except Exception as exc:
        status = "failed"
        out = {"error": str(exc)[:500]}
        raise
    finally:
        common.finish_job(eng, job, status, None, (out or {}).get("n", 0) or 0, out or {})
    return out


if __name__ == "__main__":
    main()
