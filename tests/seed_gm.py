"""Players, rosters, stats, snaps, PFR coverage, contracts, draft picks and trades for the GM-lens tests, on top of
the six-team season in tests/seed.py. Small enough to work every percentile and need score by hand (see
tests/test_gm_derive.py for the arithmetic)."""

from __future__ import annotations

import polars as pl
from sqlalchemy.engine import Connection

from db import schema
from ingest.upsert import upsert

G1, G2 = "2026_01_NYG_WAS", "2026_02_WAS_DAL"
PHI1, PHI2, DAL1 = "2026_01_DAL_PHI", "2026_02_NYG_PHI", "2026_01_DAL_PHI"

# gsis, name, team, roster position, depth slot, birth, years_exp, draft_number, pfr id
PLAYERS = [
    ("00-Q1", "Jayden Daniels", "WAS", "QB", "QB", "2000-12-18", 2, 2, "DaniJa02"),
    ("00-Q2", "Jalen Hurts", "PHI", "QB", "QB", "1998-08-07", 6, 53, "HurtJa00"),
    ("00-Q3", "Dak Prescott", "DAL", "QB", "QB", "1993-07-29", 10, 135, "PresDa01"),
    ("00-W1", "Terry McLaurin", "WAS", "WR", "WR", "1995-09-15", 7, 76, "McLaTe00"),
    ("00-W2", "Deebo Samuel", "WAS", "WR", "WR", "1996-01-15", 7, 36, "SamuDe00"),
    ("00-W3", "Antonio Williams", "WAS", "WR", "WR", "2003-05-01", 0, 71, "WillAn09"),
    ("00-W4", "A.J. Brown", "PHI", "WR", "WR", "1997-06-30", 7, 51, "BrowAJ00"),
    ("00-W5", "Malik Nabers", "NYG", "WR", "WR", "2003-07-28", 2, 6, "NabeMa00"),
    ("00-C1", "Mike Sainristil", "WAS", "DB", "CB", "2000-11-15", 2, 50, "SainMi00"),
    ("00-C2", "Deonte Banks", "NYG", "DB", "CB", "2000-12-05", 3, 24, "BankDe00"),
    ("00-O1", "Laremy Tunsil", "WAS", "OL", "T", "1994-08-02", 10, 13, "TunsLa00"),
    ("00-E1", "Odafe Oweh", "WAS", "DL", "DE", "1999-01-15", 5, 31, "OwehOd00"),
    ("00-E2", "Dorance Armstrong", "WAS", "DL", "DE", "1997-06-25", 8, 116, "ArmsDo00"),
    ("00-I1", "Javon Kinlaw", "WAS", "DL", "DT", "1997-10-03", 6, 14, "KinlJa00"),
    ("00-K1", "Matt Gay", "WAS", "K", "K", "1994-03-14", 7, 145, "GayxMa00"),
    ("00-L1", "Bobby Wagner", "WAS", "LB", "ILB", "1990-06-27", 14, 47, "WagnBo00"),
]
# on WAS at the end of 2025 (Oweh and the 2026 rookie Williams were not)
WAS_2025 = ["00-Q1", "00-W1", "00-W2", "00-C1", "00-O1", "00-E2", "00-I1", "00-K1", "00-L1"]

# otc_id, gsis, player, OTC position, team, year_signed, years, apy, guaranteed, active
CONTRACTS = [
    ("c-q1", "00-Q1", "Jayden Daniels", "QB", "WAS", 2024, 4, 9.4, 37.7, True),
    ("c-q2", "00-Q2", "Jalen Hurts", "QB", "PHI", 2023, 5, 51.0, 179.3, True),
    ("c-q3", "00-Q3", "Dak Prescott", "QB", "DAL", 2024, 4, 60.0, 231.0, True),
    ("c-w1", "00-W1", "Terry McLaurin", "WR", "WAS", 2025, 3, 32.3, 44.65, True),
    ("c-w2old", "00-W2", "Deebo Samuel", "WR", "SF", 2022, 3, 23.85, 41.0, False),
    ("c-w2", "00-W2", "Deebo Samuel", "WR", "WAS", 2026, 1, 17.5, 15.0, True),
    ("c-w3", "00-W3", "Antonio Williams", "WR", "WAS", 2026, 4, 1.81, 1.2, True),
    ("c-w4", "00-W4", "A.J. Brown", "WR", "PHI", 2024, 3, 32.0, 84.0, True),
    ("c-w5", "00-W5", "Malik Nabers", "WR", "NYG", 2024, 4, 7.3, 29.2, True),
    ("c-c1", "00-C1", "Mike Sainristil", "CB", "WAS", 2024, 4, 1.2, 1.0, True),
    ("c-c2", "00-C2", "Deonte Banks", "CB", "NYG", 2023, 4, 3.5, 14.0, True),
    ("c-o1", "00-O1", "Laremy Tunsil", "LT", "WAS", 2026, 2, 30.1, 52.7, True),
    ("c-e1", "00-E1", "Odafe Oweh", "ED", "WAS", 2026, 4, 12.65, 50.6, True),
    ("c-e2", "00-E2", "Dorance Armstrong", "ED", "WAS", 2024, 3, 15.0, 30.0, True),
    ("c-i1", "00-I1", "Javon Kinlaw", "IDL", "WAS", 2025, 3, 15.0, 30.0, True),
    ("c-k1", "00-K1", "Matt Gay", "K", "WAS", 2025, 2, 1.5, 1.0, True),
    ("c-l1", "00-L1", "Bobby Wagner", "LB", "WAS", 2026, 1, 9.5, 9.5, True),
]


def _by(gsis: str) -> tuple:
    return next(p for p in PLAYERS if p[0] == gsis)


def _games(team: str) -> list[tuple[int, str]]:
    return {
        "WAS": [(1, G1), (2, G2)],
        "PHI": [(1, PHI1), (2, PHI2)],
        "NYG": [(1, G1), (2, PHI2)],
        "DAL": [(1, DAL1)],
    }[team]


def players_frame() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "gsis_id": g,
                "display_name": name,
                "position": pos,
                "birth_date": birth,
                "draft_pick": float(draft),
                "latest_team": team,
                "pfr_id": pfr,
            }
            for g, name, team, pos, _, birth, _, draft, pfr in PLAYERS
        ]
    )


def rosters_frame() -> pl.DataFrame:
    rows = []
    for g, name, team, pos, slot, birth, exp, draft, pfr in PLAYERS:
        for week in (1, 2):
            rows.append(
                {
                    "season": 2026,
                    "week": week,
                    "team": team,
                    "gsis_id": g,
                    "full_name": name,
                    "position": pos,
                    "depth_chart_position": slot,
                    "birth_date": birth,
                    "years_exp": float(exp),
                    "draft_number": float(draft),
                    "status": "ACT",
                    "pfr_id": pfr,
                }
            )
        if g in WAS_2025:
            rows.append({"season": 2025, "week": 18, "team": "WAS", "gsis_id": g, "full_name": name, "position": pos})
    return pl.DataFrame(rows)


def _stat_rows(gsis: str, per_game: dict) -> list[dict]:
    _, name, team, pos, *_ = _by(gsis)
    return [
        {"player_id": gsis, "game_id": gid, "season": 2026, "week": wk, "team": team, "position": pos, **per_game}
        for wk, gid in _games(team)
    ]


def player_game_stats_frame() -> pl.DataFrame:
    rows = []
    rows += _stat_rows(
        "00-Q1",
        {
            "attempts": 30,
            "sacks_suffered": 1,
            "carries": 5,
            "passing_epa": 6.0,
            "rushing_epa": 1.5,
            "passing_cpoe": 3.0,
        },
    )
    rows += _stat_rows(
        "00-Q2",
        {
            "attempts": 25,
            "sacks_suffered": 2,
            "carries": 8,
            "passing_epa": 2.5,
            "rushing_epa": 2.5,
            "passing_cpoe": -1.0,
        },
    )
    rows += _stat_rows(
        "00-Q3",
        {
            "attempts": 20,
            "sacks_suffered": 0,
            "carries": 0,
            "passing_epa": 4.0,
            "rushing_epa": 0.0,
            "passing_cpoe": 5.0,
        },
    )
    rows += _stat_rows("00-W1", {"targets": 10, "receptions": 7, "receiving_epa": 4.0})
    rows += _stat_rows("00-W2", {"targets": 8, "receptions": 5, "receiving_epa": 1.6})  # 3.2/16 == 4/20 exactly
    rows += _stat_rows("00-W3", {"targets": 3, "receptions": 2, "receiving_epa": 0.9})
    rows += _stat_rows("00-W4", {"targets": 11, "receptions": 8, "receiving_epa": 5.5})
    rows += _stat_rows("00-W5", {"targets": 10, "receptions": 7, "receiving_epa": 2.0})
    rows += _stat_rows("00-C1", {"def_tackles_solo": 4, "def_pass_defended": 1})
    rows += _stat_rows("00-C2", {"def_tackles_solo": 3})
    rows += _stat_rows("00-E1", {"def_sacks": 1.0, "def_tackles_solo": 2, "def_tackles_for_loss": 1})
    rows += _stat_rows("00-E2", {"def_sacks": 0.5, "def_tackles_solo": 2})
    rows += _stat_rows("00-I1", {"def_sacks": 0.0, "def_tackles_solo": 3, "def_tackles_for_loss": 1})
    rows += _stat_rows("00-L1", {"def_tackles_solo": 10, "def_tackles_for_loss": 1})
    return pl.DataFrame(rows)


def _snap_rows(gsis: str, side: str, snaps: int, pct: float) -> list[dict]:
    _, name, team, pos, *_ = _by(gsis)
    pfr = _by(gsis)[8]
    zero = {
        "offense_snaps": 0,
        "offense_pct": 0.0,
        "defense_snaps": 0,
        "defense_pct": 0.0,
        "st_snaps": 0,
        "st_pct": 0.0,
    }
    return [
        {
            "pfr_player_id": pfr,
            "game_id": gid,
            "gsis_id": gsis,
            "season": 2026,
            "week": wk,
            "team": team,
            "player": name,
            "position": pos,
            **zero,
            f"{side}_snaps": snaps,
            f"{side}_pct": pct,
        }
        for wk, gid in _games(team)
    ]


def snap_counts_frame() -> pl.DataFrame:
    rows = []
    for gsis, side, snaps, pct in [
        ("00-Q1", "offense", 65, 1.0),
        ("00-Q2", "offense", 60, 1.0),
        ("00-Q3", "offense", 60, 1.0),
        ("00-W1", "offense", 60, 0.95),
        ("00-W2", "offense", 55, 0.9),
        ("00-W3", "offense", 25, 0.4),
        ("00-W4", "offense", 58, 0.92),
        ("00-W5", "offense", 62, 0.97),
        ("00-C1", "defense", 65, 1.0),
        ("00-C2", "defense", 60, 0.95),
        ("00-O1", "offense", 65, 1.0),
        ("00-E1", "defense", 50, 0.75),
        ("00-E2", "defense", 50, 0.75),
        ("00-I1", "defense", 40, 0.6),
        ("00-K1", "st", 5, 0.2),
        ("00-L1", "defense", 65, 1.0),
    ]:
        rows += _snap_rows(gsis, side, snaps, pct)
    return pl.DataFrame(rows)


def pfr_def_frame() -> pl.DataFrame:
    rows = []
    for gsis, per_game in [
        ("00-C1", {"def_targets": 5, "def_passer_rating_allowed": 60.0, "def_pressures": 0, "def_sacks": 0.0}),
        ("00-C2", {"def_targets": 6, "def_passer_rating_allowed": 120.0, "def_pressures": 0, "def_sacks": 0.0}),
        ("00-E1", {"def_targets": 0, "def_passer_rating_allowed": None, "def_pressures": 5, "def_sacks": 1.0}),
        ("00-E2", {"def_targets": 0, "def_passer_rating_allowed": None, "def_pressures": 3, "def_sacks": 0.5}),
        ("00-I1", {"def_targets": 0, "def_passer_rating_allowed": None, "def_pressures": 2, "def_sacks": 0.0}),
    ]:
        _, name, team, *_ = _by(gsis)
        for wk, gid in _games(team):
            rows.append(
                {
                    "pfr_player_id": _by(gsis)[8],
                    "game_id": gid,
                    "gsis_id": gsis,
                    "season": 2026,
                    "week": wk,
                    "team": team,
                    **per_game,
                }
            )
    return pl.DataFrame(rows)


def contracts_frame() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "otc_id": otc,
                "year_signed": ys,
                "team_raw": team,
                "team_abbr": team,
                "player": name,
                "position": pos,
                "gsis_id": g,
                "is_active": active,
                "years": years,
                "apy": apy,
                "guaranteed": gtd,
            }
            for otc, g, name, pos, team, ys, years, apy, gtd, active in CONTRACTS
        ]
    )


def draft_picks_frame() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "season": 2026,
                "round": 3,
                "pick": 71,
                "team": "WAS",
                "gsis_id": "00-W3",
                "pfr_player_name": "Antonio Williams",
                "position": "WR",
            },
            {
                "season": 2026,
                "round": 1,
                "pick": 6,
                "team": "NYG",
                "gsis_id": "00-X1",
                "pfr_player_name": "Someone Else",
                "position": "CB",
            },
        ]
    )


def trades_frame() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "trade_id": 7,
                "seq": 0,
                "season": 2025,
                "trade_date": "2025-03-01",
                "gave": "SF",
                "received": "WAS",
                "pfr_id": "SamuDe00",
                "pfr_name": "Deebo Samuel",
                "gsis_id": "00-W2",
            },
            {
                "trade_id": 7,
                "seq": 1,
                "season": 2025,
                "trade_date": "2025-03-01",
                "gave": "WAS",
                "received": "SF",
                "pfr_id": None,
                "pfr_name": None,
                "gsis_id": None,
            },
        ]
    )


def load(conn: Connection) -> None:
    s = schema
    upsert(conn, s.players, players_frame(), ["gsis_id"])
    upsert(conn, s.rosters_weekly, rosters_frame(), ["season", "week", "team", "gsis_id"])
    upsert(conn, s.player_game_stats, player_game_stats_frame(), ["player_id", "game_id"])
    upsert(conn, s.snap_counts, snap_counts_frame(), ["pfr_player_id", "game_id"])
    upsert(conn, s.pfr_def_game, pfr_def_frame(), ["pfr_player_id", "game_id"])
    upsert(conn, s.contracts, contracts_frame(), ["otc_id", "year_signed", "team_raw"])
    upsert(conn, s.draft_picks, draft_picks_frame(), ["season", "round", "pick"])
    upsert(conn, s.trades, trades_frame(), ["trade_id", "seq"])
