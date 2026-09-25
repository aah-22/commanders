"""The schema migrates from nothing on SQLite (Postgres schemas become plain tables there)."""

import os
import subprocess
import sys


def test_alembic_upgrade_head_from_scratch(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": os.getcwd()}
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True, env=env, check=False
    )
    assert proc.returncode == 0, proc.stderr
    import sqlalchemy as sa

    with sa.create_engine(url).connect() as c:
        names = set(sa.inspect(c).get_table_names())
    assert {"games", "pipeline_runs", "team_game_stats", "team_game_summary", "standings"} <= names
    with sa.create_engine(url).connect() as c:
        cols = {col["name"] for col in sa.inspect(c).get_columns("plays")}
    assert "qb_epa" in cols
