"""Derived (gm.*) tables, rebuilt per season from the mirrors after every ingest."""

from __future__ import annotations

import os

from sqlalchemy.engine import Connection


def team() -> str:
    return os.environ.get("TEAM", "WAS")


def run_season(conn: Connection, season: int) -> dict[str, int]:
    from ingest.derive import acquisitions, need, production, standings, team_game_summary

    t = team()
    return {
        "team_game_summary": team_game_summary.run_season(conn, season),
        "standings": standings.run_season(conn, season),
        "player_season_production": production.run_season(conn, season),
        "acquisitions": acquisitions.run_season(conn, season, t),
        "positional_need": need.run_season(conn, season, t),
    }
