"""Response models for /v1/gm/* and /v1/models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AcquisitionCard(BaseModel):
    gsis_id: str
    name: str | None = None
    position: str | None = None
    pos_group: str | None = None
    how: str
    date: str | None = None
    from_team: str | None = None
    draft_round: int | None = None
    draft_pick: int | None = None
    arrival_season: int
    current_team: str | None = None
    apy: float | None = None
    contract_years: int | None = None
    guaranteed: float | None = None
    year_signed: int | None = None
    years_left: int | None = None
    age: float | None = None
    games: int | None = None
    snaps: int | None = None
    snap_share: float | None = None
    metric: str | None = None
    production: float | None = None
    production_pct: float | None = None
    qualified: bool | None = None
    cost_pct: float | None = None
    graded_seasons: list[int] = []  # the qualified seasons on the team since arrival that the grade pools
    tenure_pct: float | None = None  # snap-weighted production percentile over those seasons
    expected_pct: float | None = None
    basis: str  # "model" (acquisition-value champion), "cost" (APY percentile), or "mixed" across seasons
    value_gap: float | None = None
    grade: str | None = None
    run_id: str | None = None
    model_version: str | None = None


class Acquisitions(BaseModel):
    season: int
    team: str
    since: int
    cards: list[AcquisitionCard]


class Starter(BaseModel):
    gsis_id: str
    name: str | None = None
    position: str | None = None
    age: float | None = None
    snap_share: float | None = None
    production_pct: float | None = None
    years_left: int | None = None
    apy: float | None = None


class NeedGroup(BaseModel):
    pos_group: str
    starters: int
    starter_pct: float | None = None
    starters_expiring: int
    starters_aging: int
    avg_age: float | None = None
    contract_years_left: float | None = None
    depth: int
    need_score: float
    need_rank: int | None = None
    starter_list: list[Starter]


class Need(BaseModel):
    season: int
    team: str
    groups: list[NeedGroup]


class Target(BaseModel):
    gsis_id: str
    name: str | None = None
    team: str | None = None
    position: str | None = None
    pos_group: str | None = None
    age: float | None = None
    games: int | None = None
    production_pct: float | None = None
    projected_pct: float | None = None
    projection_run_id: str | None = None
    apy: float | None = None
    years_left: int | None = None
    reason: str | None = None
    need_score: float | None = None
    score: float
    run_id: str | None = None
    version: str | None = None


class Targets(BaseModel):
    season: int
    team: str
    position: str | None = None
    live: bool  # True when computed on request because the nightly score has not run for this season yet
    scored_at: str | None = None
    targets: list[Target]


class ModelOutputSummary(BaseModel):
    model: str
    season: int
    version: str | None = None
    run_id: str | None = None
    rows: int
    scored_at: str | None = None


class JobSummary(BaseModel):
    kind: str
    status: str
    season: int | None = None
    finished_at: str
    detail: dict[str, Any]


class Models(BaseModel):
    experiment: str
    tracking: str
    outputs: list[ModelOutputSummary]
    jobs: list[JobSummary]
