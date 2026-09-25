"""phase 2: nfl.team_game_stats mirror, gm.team_game_summary and gm.standings; plays gains qb_epa

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

from db import schema

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NEW_TABLES = ["team_game_stats", "team_game_summary", "standings"]


def _bind():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else bind.execution_options(**schema.sqlite_options())


def _tables():
    return [schema.metadata.tables[k] for k in schema.metadata.tables if k.split(".")[-1] in NEW_TABLES]


def upgrade() -> None:
    bind = _bind()
    nfl = "nfl" if bind.dialect.name == "postgresql" else None
    # A database migrated from scratch already has the column (0002 creates `plays` from the current model).
    if "qb_epa" not in {c["name"] for c in sa.inspect(bind).get_columns("plays", schema=nfl)}:
        op.add_column("plays", sa.Column("qb_epa", sa.Float), schema=nfl)
    schema.metadata.create_all(bind=bind, tables=_tables())


def downgrade() -> None:
    bind = _bind()
    schema.metadata.drop_all(bind=bind, tables=_tables())
    nfl = "nfl" if bind.dialect.name == "postgresql" else None
    with op.batch_alter_table("plays", schema=nfl) as batch:
        batch.drop_column("qb_epa")
