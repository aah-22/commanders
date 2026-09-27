"""Score the season with the champions and write ml.model_outputs (delete-then-insert per model and season).

    python -m models.score              # SEASON from the environment, else the current one

`production-next`: projected next-season production percentile for every qualified player.
`acquisition-value`: the percentile a player's contract usually buys; the gap to his actual percentile is the grade.
`target-rank`: not a learned model but a tracked formula — for every player not on the team who is a pending free
agent (contract ends this season) or productive on a losing team (win % ≤ .350), need score × projected percentile ×
an age discount; its rows carry this scoring run's id, the model rows carry their champion's run id."""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive import positions as pos
from ingest.lineage import Tracker
from models import common, features

log = logging.getLogger("models.score")
LOSING = 0.35
AGE_DISCOUNT = 0.7
FORMULA_VERSION = "formula-1"
VALUE_SEASONS_BACK = 2  # the report cards cover this season and the two before it


def write(conn: Connection, model: str, season: int, rows: list[dict]) -> int:
    t = schema.model_outputs
    conn.execute(t.delete().where(t.c.model == model, t.c.season == season))
    if rows:
        conn.execute(t.insert(), rows)
    return len(rows)


def _rows(model: str, season: int, version: str, run_id: str | None, ids, values, details) -> list[dict]:  # noqa: ANN001
    now = datetime.now(UTC)
    return [
        {
            "model": model,
            "season": season,
            "gsis_id": g,
            "version": version,
            "run_id": run_id,
            "value": float(v),
            "detail": d,
            "scored_at": now,
        }
        for g, v, d in zip(ids, values, details, strict=True)
    ]


def score_production_next(tr: Tracker, frame: pd.DataFrame, season: int) -> tuple[list[dict], dict]:
    champ = common.champion(tr, "production-next")
    if champ is None:
        return [], {}
    model, version, run_id = champ
    cur = features.with_prev(frame)
    cur = cur[(cur["season"] == season) & cur["qualified"].astype(bool) & cur["production_pct"].notna()]
    if cur.empty:
        return [], {}
    pred = model.predict(cur[features.NEXT_FEATURES]).clip(0, 1)
    details = [
        {"production_pct": float(p), "pos_group": g}
        for p, g in zip(cur["production_pct"], cur["pos_group"], strict=True)
    ]
    return _rows("production-next", season, version, run_id, cur["gsis_id"], pred, details), {
        "version": version,
        "run_id": run_id,
    }


def score_acquisition_value(tr: Tracker, frame: pd.DataFrame, season: int) -> tuple[list[dict], dict]:
    champ = common.champion(tr, "acquisition-value")
    if champ is None:
        return [], {}
    model, version, run_id = champ
    cur = frame[(frame["season"] == season) & frame["cost_pct"].notna()]
    if cur.empty:
        return [], {}
    pred = model.predict(cur[features.VALUE_FEATURES]).clip(0, 1)
    details = [
        {
            "cost_pct": float(c),
            "production_pct": None if pd.isna(p) else float(p),
            "gap": None if pd.isna(p) else float(p - e),
        }
        for c, p, e in zip(cur["cost_pct"], cur["production_pct"], pred, strict=True)
    ]
    return _rows("acquisition-value", season, version, run_id, cur["gsis_id"], pred, details), {
        "version": version,
        "run_id": run_id,
    }


def losing_teams(conn: Connection, season: int) -> set[str]:
    st = schema.standings
    latest = select(st.c.team, st.c.win_pct).where(st.c.season == season).order_by(st.c.week.desc())
    seen: dict[str, float | None] = {}
    for team, wp in conn.execute(latest):
        seen.setdefault(team, wp)
    return {t for t, wp in seen.items() if wp is not None and wp <= LOSING}


def score_targets(
    conn: Connection, frame: pd.DataFrame, season: int, team: str, projections: dict[str, float], run_id: str | None
) -> list[dict]:
    need_t = schema.positional_need
    need = {
        g: s
        for g, s in conn.execute(
            select(need_t.c.pos_group, need_t.c.need_score).where(need_t.c.season == season, need_t.c.team == team)
        )
    }
    losing = losing_teams(conn, season)
    cur = frame[(frame["season"] == season) & (frame["team"] != team) & frame["production_pct"].notna()]
    ids, values, details = [], [], []
    for r in cur.itertuples(index=False):
        if r.pos_group not in need:
            continue
        pending = r.years_left is not None and not pd.isna(r.years_left) and r.years_left <= 0
        losing_team = r.team in losing
        if not (pending or losing_team):
            continue
        proj = projections.get(r.gsis_id, float(r.production_pct))
        young = pd.isna(r.age) or r.age < pos.AGING.get(r.pos_group, 99)
        score = need[r.pos_group] / 100 * proj * (1.0 if young else AGE_DISCOUNT)
        ids.append(r.gsis_id)
        values.append(score)
        details.append(
            {
                "reason": "pending free agent" if pending else "losing team",
                "projected_pct": float(proj),
                "need_score": float(need[r.pos_group]),
                "apy": None if pd.isna(r.apy) else float(r.apy),
                "pos_group": r.pos_group,
            }
        )
    return _rows("target-rank", season, FORMULA_VERSION, run_id, ids, values, details)


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description="score the season with the champion models")
    ap.add_argument("--season", type=int)
    ap.add_argument("--no-mlflow", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s %(message)s")
    season, team = a.season or common.season(), common.team()
    tr = Tracker(not a.no_mlflow)
    eng = common.engine()
    job = common.start_job(eng, "score", season)
    t0, status, counts, lineage = time.time(), "ok", {}, {}
    try:
        with tr.run(f"score-{season}-{datetime.now(UTC):%Y%m%d}", {"stage": "score", "season": season}) as run_id:
            with eng.begin() as conn:
                frame = features.production_frame(conn)
                nxt, lin = score_production_next(tr, frame, season)
                lineage["production-next"] = lin
                counts["production-next"] = write(conn, "production-next", season, nxt)
                counts["acquisition-value"] = 0
                for s in range(season - VALUE_SEASONS_BACK, season + 1):
                    val, lin = score_acquisition_value(tr, frame, s)
                    lineage["acquisition-value"] = lin or lineage.get("acquisition-value", {})
                    counts["acquisition-value"] += write(conn, "acquisition-value", s, val)
                projections = {r["gsis_id"]: r["value"] for r in nxt}
                targets = score_targets(conn, frame, season, team, projections, run_id)
                counts["target-rank"] = write(conn, "target-rank", season, targets)
            tr.params(
                {"season": season, "team": team, **{f"{k}_version": v.get("version") for k, v in lineage.items()}}
            )
            tr.metrics(counts)
            for k, n in counts.items():
                log.info("%s: %s rows", k, n)
    except Exception as exc:
        status = "failed"
        counts["error"] = str(exc)[:500]
        raise
    finally:
        common.finish_job(
            eng,
            job,
            status,
            None,
            sum(v for v in counts.values() if isinstance(v, int)),
            {**counts, "seconds": time.time() - t0},
        )
    return counts


if __name__ == "__main__":
    main()
