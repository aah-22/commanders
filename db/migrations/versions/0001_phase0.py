"""phase 0: ops.pipeline_runs and nfl.games

Revision ID: 0001
Revises:
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _schema(name: str) -> str | None:
    return name if op.get_bind().dialect.name == "postgresql" else None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(16), index=True),
        sa.Column("run_id", sa.String(64)),
        sa.Column("season", sa.Integer),
        sa.Column("status", sa.String(16)),
        sa.Column("rows", sa.Integer),
        sa.Column("detail", sa.JSON),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        schema=_schema("ops"),
    )
    op.create_table(
        "games",
        sa.Column("game_id", sa.String(24), primary_key=True),
        sa.Column("season", sa.Integer, index=True),
        sa.Column("week", sa.Integer, index=True),
        sa.Column("game_type", sa.String(8)),
        sa.Column("gameday", sa.String(10)),
        sa.Column("gametime", sa.String(8)),
        sa.Column("home_team", sa.String(4), index=True),
        sa.Column("away_team", sa.String(4), index=True),
        sa.Column("home_score", sa.Integer),
        sa.Column("away_score", sa.Integer),
        sa.Column("result", sa.Integer),
        sa.Column("total", sa.Integer),
        sa.Column("roof", sa.String(16)),
        sa.Column("surface", sa.String(16)),
        sa.Column("stadium", sa.Text),
        schema=_schema("nfl"),
    )


def downgrade() -> None:
    op.drop_table("games", schema=_schema("nfl"))
    op.drop_table("pipeline_runs", schema=_schema("ops"))
