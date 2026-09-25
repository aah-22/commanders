"""nflverse → Postgres.  python -m ingest.run --nightly | --full --seasons 2016-2026 [--jobs plays,snap_counts]

Every table is upserted on its natural key (re-running on unchanged data changes nothing); each asset's digest is
kept in ops.dataset_versions so an unchanged file is skipped; one MLflow run per invocation records row counts and a
dataset per source. Season-scoped assets loop per season so memory stays flat (pbp is ~110 MB a season in memory).
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import time
from datetime import UTC, datetime

import pandas as pd
import polars as pl
from sqlalchemy import create_engine, text

from db import schema
from ingest import loaders
from ingest.lineage import Tracker
from ingest.sources import FIRST_SEASON, SOURCES
from ingest.upsert import upsert

log = logging.getLogger("ingest")

SEASON_JOBS = [
    "games",
    "plays",
    "player_game_stats",
    "snap_counts",
    "rosters_weekly",
    "depth_charts",
    "injuries",
    "pfr_def_game",
    "pfr_pass_game",
    "pfr_rush_game",
    "pfr_rec_game",
    "ngs_passing",
    "ngs_rushing",
    "ngs_receiving",
]
GLOBAL_JOBS = ["teams", "players", "contracts", "draft_picks", "trades"]


def engine():
    url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
    eng = create_engine(url, future=True)
    if eng.dialect.name != "postgresql":
        eng = eng.execution_options(**schema.sqlite_options())
    return eng


def digest(df: pl.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(str(df.shape).encode())
    if not df.is_empty():
        h.update(df.hash_rows().sort().to_numpy().tobytes())
    return h.hexdigest()


def current_season() -> int:
    now = datetime.now(UTC)
    return now.year if now.month >= 3 else now.year - 1


class Ingest:
    def __init__(self, conn, tracker: Tracker, cache_mode: str = "off"):
        import nflreadpy as nfl

        self.nfl, self.conn, self.tr = nfl, conn, tracker
        nfl.config.update_config(
            cache_mode=cache_mode, cache_dir=os.path.join(os.environ.get("DATA_DIR", "."), "nflreadpy")
        )
        self.rows: dict[str, int] = {}
        self.skipped: list[str] = []
        self._players: pl.DataFrame | None = None
        self._teams: pl.DataFrame | None = None
        self._schedule: pl.DataFrame | None = None

    # ---------------------------------------------------------------- helpers
    def _write(self, name: str, df: pl.DataFrame, season: int = 0) -> int:
        url, key = SOURCES[name]
        url = url.format(season=season)
        d = digest(df)
        prev = self.conn.execute(
            text("SELECT digest FROM ops.dataset_versions WHERE dataset=:d AND season=:s")
            if self.conn.dialect.name == "postgresql"
            else text("SELECT digest FROM dataset_versions WHERE dataset=:d AND season=:s"),
            {"d": name, "s": season},
        ).scalar()
        if prev == d:
            self.skipped.append(f"{name}:{season}" if season else name)
            return 0
        n = upsert(self.conn, schema.MIRRORS[name], df, key)
        upsert(
            self.conn,
            schema.DatasetVersion.__table__,
            pl.DataFrame(
                {
                    "dataset": [name],
                    "season": [season],
                    "source_url": [url],
                    "digest": [d],
                    "rows": [df.height],
                    "fetched_at": [datetime.now(UTC)],
                }
            ),
            ["dataset", "season"],
        )
        self.rows[f"{name}_{season}" if season else name] = n
        summary = (
            df.group_by("week").len().sort("week").to_pandas()
            if "week" in df.columns and season
            else pd.DataFrame({"rows": [df.height]})
        )
        self.tr.dataset(f"{name}-{season or 'all'}", url, summary)
        return n

    @property
    def players_df(self) -> pl.DataFrame:
        if self._players is None:
            self._players = loaders.players(self.nfl.load_players())
        return self._players

    @property
    def teams_df(self) -> pl.DataFrame:
        if self._teams is None:
            self._teams = loaders.teams(self.nfl.load_teams())
        return self._teams

    def schedule(self, season: int) -> pl.DataFrame:
        if self._schedule is None or self._schedule.filter(pl.col("season") == season).is_empty():
            self._schedule = loaders.games(self.nfl.load_schedules([season]))
        return self._schedule

    # ---------------------------------------------------------------- jobs
    def global_job(self, name: str) -> None:
        nfl = self.nfl
        if name == "teams":
            self._write("teams", self.teams_df)
        elif name == "players":
            self._write("players", self.players_df)
        elif name == "contracts":
            flat, seasons = loaders.contracts(nfl.load_contracts(), loaders.team_map_from_teams(self.teams_df))
            self._write("contracts", flat)
            self._write("contract_seasons", seasons)
        elif name == "draft_picks":
            self._write("draft_picks", loaders.draft_picks(nfl.load_draft_picks()))
        elif name == "trades":
            self._write("trades", loaders.trades(nfl.load_trades(), loaders.id_map_from_players(self.players_df)))

    def season_job(self, name: str, season: int) -> None:
        nfl, ids = self.nfl, loaders.id_map_from_players(self.players_df)
        if name == "games":
            self._write("games", self.schedule(season), season)
        elif name == "plays":
            self._write("plays", loaders.plays(nfl.load_pbp([season])), season)
        elif name == "player_game_stats":
            self._write(
                "player_game_stats",
                loaders.player_game_stats(nfl.load_player_stats([season], summary_level="week")),
                season,
            )
        elif name == "snap_counts":
            self._write("snap_counts", loaders.snap_counts(nfl.load_snap_counts([season]), ids), season)
        elif name == "rosters_weekly":
            self._write("rosters_weekly", loaders.rosters_weekly(nfl.load_rosters_weekly([season])), season)
        elif name == "depth_charts":
            self._write(
                "depth_charts",
                loaders.depth_charts(nfl.load_depth_charts([season]), self.schedule(season), season),
                season,
            )
        elif name == "injuries":
            self._write("injuries", loaders.injuries(nfl.load_injuries([season])), season)
        elif name.startswith("pfr_"):
            kind = name.split("_")[1]
            self._write(
                name, loaders.pfr(nfl.load_pfr_advstats([season], stat_type=kind, summary_level="week"), ids), season
            )
        elif name.startswith("ngs_"):
            kind = name.split("_")[1]
            self._write(name, loaders.ngs(nfl.load_nextgen_stats([season], stat_type=kind)), season)


def parse_seasons(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(s) for s in spec.split(",")]


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description="nflverse → Postgres")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--nightly", action="store_true", help="current season, every job, no cache")
    mode.add_argument("--full", action="store_true", help="backfill --seasons (default 2016-current), filesystem cache")
    mode.add_argument("--season", type=int, help="one season (with --jobs for a targeted refresh)")
    ap.add_argument("--seasons", help="e.g. 2016-2026 or 2024,2025")
    ap.add_argument("--jobs", help="comma-separated subset of " + ",".join(GLOBAL_JOBS + SEASON_JOBS))
    ap.add_argument("--no-mlflow", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s %(message)s")

    seasons = (
        parse_seasons(a.seasons)
        if a.seasons
        else (
            [a.season]
            if a.season
            else (list(range(FIRST_SEASON, current_season() + 1)) if a.full else [current_season()])
        )
    )
    jobs = a.jobs.split(",") if a.jobs else GLOBAL_JOBS + SEASON_JOBS
    tr = Tracker(not a.no_mlflow)
    t0 = time.time()
    eng = engine()
    with eng.begin() as conn:
        run_row = conn.execute(
            schema.PipelineRun.__table__.insert()
            .values(kind="ingest", status="running")
            .returning(schema.PipelineRun.id)
        ).scalar()
    status, detail = "ok", {}
    with tr.run(
        f"ingest-{datetime.now(UTC):%Y%m%d-%H%M}", {"stage": "ingest", "mode": "full" if a.full else "nightly"}
    ) as run_id:
        tr.params({"seasons": seasons, "jobs": jobs})
        try:
            with eng.begin() as conn:
                ing = Ingest(conn, tr, cache_mode="filesystem" if a.full else "off")
                for j in [j for j in jobs if j in GLOBAL_JOBS]:
                    log.info("job %s", j)
                    ing.global_job(j)
                for s in seasons:
                    for j in [j for j in jobs if j in SEASON_JOBS]:
                        log.info("job %s season %s", j, s)
                        try:
                            ing.season_job(j, s)
                        except Exception as exc:  # noqa: BLE001  — one missing asset (not published yet) must not sink the run
                            log.warning("job %s season %s failed: %s", j, s, str(exc)[:200])
                            detail[f"{j}_{s}"] = str(exc)[:200]
                detail.update({"rows": ing.rows, "skipped": ing.skipped})
                tr.metrics({k: v for k, v in ing.rows.items()})
                tr.metrics(
                    {
                        "skipped_datasets": len(ing.skipped),
                        "failed_jobs": len([k for k in detail if k not in ("rows", "skipped")]),
                    }
                )
        except Exception as exc:
            status, detail["error"] = "failed", str(exc)[:500]
            raise
        finally:
            with eng.begin() as conn:
                conn.execute(
                    schema.PipelineRun.__table__.update()
                    .where(schema.PipelineRun.id == run_row)
                    .values(
                        status=status,
                        run_id=run_id,
                        rows=sum(detail.get("rows", {}).values()),
                        detail=detail,
                        finished_at=datetime.now(UTC),
                        season=seasons[-1],
                    )
                )
            tr.metrics({"seconds": time.time() - t0})
    log.info(
        "ingest complete: %s rows in %.0fs, skipped %s",
        sum(detail.get("rows", {}).values()),
        time.time() - t0,
        len(detail.get("skipped", [])),
    )
    return detail


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
