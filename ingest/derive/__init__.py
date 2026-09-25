"""Derived (gm.*) tables, rebuilt per season from the mirrors after every ingest."""

from __future__ import annotations

from sqlalchemy.engine import Connection


def run_season(conn: Connection, season: int) -> dict[str, int]:
    from ingest.derive import standings, team_game_summary

    return {
        "team_game_summary": team_game_summary.run_season(conn, season),
        "standings": standings.run_season(conn, season),
    }
