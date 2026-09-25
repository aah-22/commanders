"""A tiny hand-built season for the derive and API tests: six teams, three weeks (the third unplayed, KC/BUF on a
bye in week 2), and a WAS week-1 offence that hits every filter edge (kickoff first, sack, scramble, no-play penalty,
kneel, spike, aborted snap, completed-pass fumble with qb_epa ≠ epa, turnover on downs). The expected numbers in the
tests are worked by hand from `WAS_G1_PLAYS`."""

from __future__ import annotations

import os
import subprocess
import sys

import polars as pl
from sqlalchemy import create_engine

from db import schema
from ingest.upsert import upsert

G1 = "2026_01_NYG_WAS"
TEAMS = [
    ("WAS", "NFC", "NFC East"),
    ("PHI", "NFC", "NFC East"),
    ("DAL", "NFC", "NFC East"),
    ("NYG", "NFC", "NFC East"),
    ("KC", "AFC", "AFC West"),
    ("BUF", "AFC", "AFC East"),
]
# game_id, week, away, home, away_score, home_score, gameday
GAMES = [
    (G1, 1, "NYG", "WAS", 20, 27, "2026-09-13"),
    ("2026_01_DAL_PHI", 1, "DAL", "PHI", 20, 20, "2026-09-13"),
    ("2026_01_BUF_KC", 1, "BUF", "KC", 17, 24, "2026-09-14"),
    ("2026_02_WAS_DAL", 2, "WAS", "DAL", 20, 37, "2026-09-20"),
    ("2026_02_NYG_PHI", 2, "NYG", "PHI", 10, 30, "2026-09-20"),
    ("2026_03_PHI_WAS", 3, "PHI", "WAS", None, None, "2026-09-27"),
    ("2026_03_KC_DAL", 3, "KC", "DAL", None, None, "2026-09-27"),
]

PLAY_COLUMNS = [
    "play_id",
    "play_type",
    "fixed_drive",
    "down",
    "ydstogo",
    "yardline_100",
    "epa",
    "qb_epa",
    "success",
    "qb_dropback",
    "xpass",
    "wp",
    "yards_gained",
    "sack",
    "first_down",
    "fumble_lost",
    "aborted_play",
    "penalty",
    "fixed_drive_result",
]
# fmt: off
WAS_G1_PLAYS = [
    # id  type        drv dn ytg yl   epa   qb_epa succ db  xpass wp   yds sack fd  fl  ab  pen result
    (1,  "kickoff",   1, None, None, 65, None, None, None, 0, None, 0.5, 0,  0, 0, 0, 0, 0, "Punt"),
    (2,  "pass",      1, 1, 10, 75,  0.5, None, 1.0, 1, 0.6, 0.5, 25, 0, 1, 0, 0, 0, "Punt"),
    (3,  "run",       1, 1, 10, 50, -0.3, None, 0.0, 0, 0.5, 0.5, 2,  0, 0, 0, 0, 0, "Punt"),
    (4,  "pass",      1, 2, 8,  48, -1.0, None, 0.0, 1, 0.7, 0.5, -7, 1, 0, 0, 0, 0, "Punt"),
    (5,  "run",       1, 3, 15, 55,  0.2, None, 0.0, 1, 0.9, 0.5, 6,  0, 0, 0, 0, 0, "Punt"),
    (6,  "punt",      1, 4, 9,  49, -0.2, None, None, 0, None, 0.5, 0, 0, 0, 0, 0, 0, "Punt"),
    (7,  "pass",      3, 1, 10, 18,  1.5, None, 1.0, 1, 0.5, 0.5, 18, 0, 1, 0, 0, 0, "Touchdown"),
    (8,  "no_play",   5, 1, 10, 30, -0.5, None, 0.0, 0, 0.5, 0.5, 0,  0, 0, 0, 0, 1, "Fumble"),
    (9,  "qb_kneel",  5, 1, 15, 35, -0.4, None, 0.0, 0, None, 0.5, -1, 0, 0, 0, 0, 0, "Fumble"),
    (10, "run",       5, 2, 16, 36, -2.0, None, 0.0, 0, 0.5, 0.5, -5, 0, 0, 1, 1, 0, "Fumble"),
    (11, "qb_spike",  7, 1, 10, 50, -0.1, -0.1, 0.0, 0, None, 0.95, 0, 0, 0, 0, 0, 0, "Fumble"),
    (12, "pass",      7, 2, 5,  45, -3.0,  0.8, 0.0, 1, 0.6, 0.95, 12, 0, 1, 1, 0, 0, "Fumble"),
    (13, "pass",      9, 4, 2,  40, -1.2, None, 0.0, 1, 0.5, 0.3, 0,  0, 0, 0, 0, 0, "Turnover on downs"),
]
NYG_G1_PLAYS = [
    (20, "kickoff", 2, None, None, 65, None, None, None, 0, None, 0.5, 0, 0, 0, 0, 0, 0, "Punt"),
    (21, "pass",    2, 1, 10, 70,  0.4, None, 1.0, 1, 0.5, 0.5, 9, 0, 0, 0, 0, 0, "Punt"),
    (22, "run",     2, 2, 1,  61, -0.6, None, 0.0, 0, 0.3, 0.5, 0, 0, 0, 0, 0, 0, "Punt"),
    (23, "pass",    4, 1, 10, 80,  0.1, None, 1.0, 1, 0.5, 0.5, 5, 0, 0, 0, 0, 0, "Punt"),
]
# fmt: on


def _rows(game_id: str, week: int, posteam: str, defteam: str, plays: list[tuple]) -> list[dict]:
    out = []
    for p in plays:
        row = dict(zip(PLAY_COLUMNS, p, strict=True))
        row.update(game_id=game_id, season=2026, week=week, posteam=posteam, defteam=defteam)
        out.append(row)
    return out


def _generic(game_id: str, week: int, posteam: str, defteam: str, base: int, scale: float) -> list[dict]:
    """Eight ordinary plays with a team-specific EPA level so every team-game has a row and ranks are distinct."""
    plays = []
    for i in range(8):
        pt = "pass" if i % 2 else "run"
        plays.append(
            (
                base + i,
                pt,
                base // 100 + 1,
                1 + i % 3,
                10 if i % 3 == 0 else 5,
                60 - 5 * i,
                round(scale * (0.3 - 0.1 * (i % 4)), 3),
                None,
                1.0 if i % 4 < 2 else 0.0,
                1 if pt == "pass" else 0,
                0.5,
                0.5,
                15 if i == 1 else 4,
                0,
                1 if i % 4 < 2 else 0,
                0,
                0,
                0,
                "Field goal",
            )
        )
    return _rows(game_id, week, posteam, defteam, plays)


def plays_frame() -> pl.DataFrame:
    rows = _rows(G1, 1, "WAS", "NYG", WAS_G1_PLAYS) + _rows(G1, 1, "NYG", "WAS", NYG_G1_PLAYS)
    scale = {"WAS": 1.0, "PHI": 1.6, "DAL": 1.3, "NYG": 0.4, "KC": 1.9, "BUF": 0.7}
    for gid, week, away, home, _, _, _ in GAMES[1:5]:
        rows += _generic(gid, week, home, away, 100, scale[home]) + _generic(gid, week, away, home, 200, scale[away])
    return pl.DataFrame(rows)


def games_frame() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "game_id": gid,
                "season": 2026,
                "week": week,
                "game_type": "REG",
                "gameday": day,
                "gametime": "13:00",
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "result": None if hs is None else hs - as_,
            }
            for gid, week, away, home, as_, hs, day in GAMES
        ]
    )


def teams_frame() -> pl.DataFrame:
    return pl.DataFrame([{"team_abbr": a, "team_conf": c, "team_division": d, "team_nick": a} for a, c, d in TEAMS])


def team_game_stats_frame() -> pl.DataFrame:
    """nflverse-convention totals for the hand-built game (see the test for the arithmetic)."""
    return pl.DataFrame(
        [
            {"team": "WAS", "game_id": G1, "season": 2026, "week": 1, "passing_epa": 0.5, "rushing_epa": -2.5},
            {"team": "NYG", "game_id": G1, "season": 2026, "week": 1, "passing_epa": 0.5, "rushing_epa": -0.6},
        ]
    )


def migrated_url(tmp_path) -> str:  # noqa: ANN001
    url = f"sqlite:///{tmp_path / 'season.db'}"
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": os.getcwd()}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=env, capture_output=True)  # noqa: S603
    return url


def seed(tmp_path) -> str:  # noqa: ANN001
    """Migrate a fresh SQLite file, load the mirrors, return its URL."""
    url = migrated_url(tmp_path)
    eng = create_engine(url).execution_options(**schema.sqlite_options())
    with eng.begin() as conn:
        upsert(conn, schema.teams, teams_frame(), ["team_abbr"])
        upsert(conn, schema.Game.__table__, games_frame(), ["game_id"])
        upsert(conn, schema.plays, plays_frame(), ["game_id", "play_id"])
        upsert(conn, schema.team_game_stats, team_game_stats_frame(), ["team", "game_id"])
    return url
