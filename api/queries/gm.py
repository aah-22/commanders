"""Read-side queries for the GM pages: acquisitions with their production and model grade, positional need with the
starters behind it, the target board from ml.model_outputs (or the same formula live when nothing is scored yet),
and the model inventory for the About page."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.engine import Connection

from db import schema
from ingest.derive import positions as pos

PSP = schema.player_season_production
ACQ = schema.acquisitions
NEED = schema.positional_need
MO = schema.model_outputs
RUNS = schema.PipelineRun.__table__

PRODUCTION_FIELDS = [
    "age",
    "games",
    "snaps",
    "snap_share",
    "metric",
    "production",
    "production_pct",
    "qualified",
    "cost_pct",
    "years_left",
]


def production(conn: Connection, season: int) -> dict[str, dict]:
    rows = conn.execute(select(PSP).where(PSP.c.season == season))
    return {r.gsis_id: dict(r._mapping) for r in rows}


def outputs(conn: Connection, model: str, season: int) -> dict[str, dict]:
    rows = conn.execute(select(MO).where(MO.c.model == model, MO.c.season == season))
    return {r.gsis_id: dict(r._mapping) for r in rows}


def grade(gap: float | None) -> str | None:
    if gap is None:
        return None
    for letter, floor in (("A", 0.2), ("B", 0.08), ("C", -0.08), ("D", -0.2)):
        if gap >= floor:
            return letter
    return "F"


def acquisitions(conn: Connection, season: int, team: str, since: int) -> list[dict]:
    """Arrivals from `since` through `season`, with this season's production and the value model's expectation."""
    rows = conn.execute(
        select(ACQ)
        .where(ACQ.c.team == team, ACQ.c.season.between(since, season))
        .order_by(ACQ.c.season.desc(), ACQ.c.how)
    )
    prod = production(conn, season)
    value = outputs(conn, "acquisition-value", season)
    out = []
    for r in rows:
        a = dict(r._mapping)
        p = prod.get(a["gsis_id"], {})
        v = value.get(a["gsis_id"])
        card = {**a, "arrival_season": a["season"], **{k: p.get(k) for k in PRODUCTION_FIELDS}}
        card["current_team"] = p.get("team")
        card["pos_group"] = a["pos_group"] or p.get("pos_group")
        actual = p.get("production_pct")
        if v is not None:
            card.update(expected_pct=v["value"], basis="model", run_id=v["run_id"], model_version=v["version"])
        else:
            card.update(expected_pct=p.get("cost_pct"), basis="cost", run_id=None, model_version=None)
        gap = actual - card["expected_pct"] if actual is not None and card["expected_pct"] is not None else None
        card["value_gap"] = gap
        card["grade"] = grade(gap)
        out.append(card)
    out.sort(key=lambda c: (-c["arrival_season"], c["how"], -(c["apy"] or 0)))
    return out


def need(conn: Connection, season: int, team: str) -> list[dict]:
    rows = [dict(r._mapping) for r in conn.execute(select(NEED).where(NEED.c.season == season, NEED.c.team == team))]
    mine = [
        dict(r._mapping)
        for r in conn.execute(
            select(PSP)
            .where(PSP.c.season == season, PSP.c.team == team)
            .order_by(PSP.c.pos_group, PSP.c.snap_share.desc().nulls_last())
        )
    ]
    for g in rows:
        players = [p for p in mine if p["pos_group"] == g["pos_group"]][: pos.STARTERS[g["pos_group"]]]
        g["starter_list"] = [
            {
                "gsis_id": p["gsis_id"],
                "name": p["name"],
                "position": p["position"],
                "age": p["age"],
                "snap_share": p["snap_share"],
                "production_pct": p["production_pct"],
                "years_left": p["years_left"],
                "apy": p["apy"],
            }
            for p in players
        ]
    return sorted(rows, key=lambda g: g["need_rank"] or 99)


def targets(conn: Connection, season: int, team: str, position: str | None, per_group: int) -> dict:
    scored = outputs(conn, "target-rank", season)
    live = False
    if not scored:
        live = True
        from models import features
        from models.score import score_targets

        frame = features.production_frame(conn)
        scored = {r["gsis_id"]: r for r in score_targets(conn, frame, season, team, {}, None)}
    prod = production(conn, season)
    proj = outputs(conn, "production-next", season)
    rows = []
    for gsis, s in scored.items():
        p = prod.get(gsis)
        if p is None or (position and p["pos_group"] != position):
            continue
        d = s["detail"] or {}
        rows.append(
            {
                "gsis_id": gsis,
                "name": p["name"],
                "team": p["team"],
                "position": p["position"],
                "pos_group": p["pos_group"],
                "age": p["age"],
                "games": p["games"],
                "production_pct": p["production_pct"],
                "projected_pct": d.get("projected_pct"),
                "projection_run_id": (proj.get(gsis) or {}).get("run_id"),
                "apy": p["apy"],
                "years_left": p["years_left"],
                "reason": d.get("reason"),
                "need_score": d.get("need_score"),
                "score": s["value"],
                "run_id": s.get("run_id"),
                "version": s.get("version"),
            }
        )
    rows.sort(key=lambda r: -r["score"])
    if not position:
        seen: dict[str, int] = {}
        kept = []
        for r in rows:
            seen[r["pos_group"]] = seen.get(r["pos_group"], 0) + 1
            if seen[r["pos_group"]] <= per_group:
                kept.append(r)
        rows = kept
    scored_at = None if live else max((s["scored_at"] for s in scored.values() if s.get("scored_at")), default=None)
    return {"targets": rows, "live": live, "scored_at": str(scored_at) if scored_at else None}


def models(conn: Connection) -> dict:
    """What the registry has produced: per model and season the version, run and row count; plus the last jobs."""
    agg = conn.execute(
        select(MO.c.model, MO.c.season, MO.c.version, MO.c.run_id, func.count().label("rows"), func.max(MO.c.scored_at))
        .group_by(MO.c.model, MO.c.season, MO.c.version, MO.c.run_id)
        .order_by(MO.c.model, MO.c.season.desc())
    )
    outputs_ = [
        {"model": m, "season": s, "version": v, "run_id": r, "rows": n, "scored_at": str(t) if t else None}
        for m, s, v, r, n, t in agg
    ]
    jobs = []
    for kind in ("ingest", "train", "score", "evaluate"):
        row = conn.execute(
            select(RUNS.c.kind, RUNS.c.status, RUNS.c.season, RUNS.c.finished_at, RUNS.c.detail)
            .where(and_(RUNS.c.kind == kind, RUNS.c.finished_at.is_not(None)))
            .order_by(RUNS.c.finished_at.desc())
            .limit(1)
        ).first()
        if row:
            jobs.append(
                {
                    "kind": row.kind,
                    "status": row.status,
                    "season": row.season,
                    "finished_at": str(row.finished_at),
                    "detail": row.detail or {},
                }
            )
    return {"outputs": outputs_, "jobs": jobs}
