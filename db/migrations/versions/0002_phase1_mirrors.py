"""phase 1: nflverse mirrors (nfl.*) and ops.dataset_versions; games gains the remaining schedule columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

from db import schema

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

NEW_GAME_COLUMNS = {
    "weekday": sa.String(10), "overtime": sa.Integer, "div_game": sa.Integer, "location": sa.String(8),
    "temp": sa.Integer, "wind": sa.Integer, "away_qb_id": sa.String(16), "home_qb_id": sa.String(16),
    "away_qb_name": sa.String(64), "home_qb_name": sa.String(64), "away_coach": sa.String(64),
    "home_coach": sa.String(64), "away_rest": sa.Integer, "home_rest": sa.Integer,
}
NEW_TABLES = [name for name in schema.MIRRORS if name != "games"] + ["dataset_versions"]


def _bind():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else bind.execution_options(**schema.sqlite_options())


def upgrade() -> None:
    bind = _bind()
    games_schema = "nfl" if bind.dialect.name == "postgresql" else None
    for name, type_ in NEW_GAME_COLUMNS.items():
        op.add_column("games", sa.Column(name, type_), schema=games_schema)
    tables = [schema.metadata.tables[k] for k in schema.metadata.tables if k.split(".")[-1] in NEW_TABLES]
    schema.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    bind = _bind()
    tables = [schema.metadata.tables[k] for k in schema.metadata.tables if k.split(".")[-1] in NEW_TABLES]
    schema.metadata.drop_all(bind=bind, tables=tables)
    games_schema = "nfl" if bind.dialect.name == "postgresql" else None
    for name in NEW_GAME_COLUMNS:
        op.drop_column("games", name, schema=games_schema)
