"""widen every bounded varchar in the nfl mirrors to text

nflverse values overflowed `players.college_name` (102 chars against varchar(64)), `contracts.draft_team` (10 vs 4),
`contracts.date_of_birth` (18 vs 10) and `rosters_weekly.college` (68 vs 64) on the first production backfill.
Upstream text is outside our control, so every string column in the `nfl` schema becomes unbounded `text` (the
model now declares them that way; a database migrated from scratch already has text and this is a no-op).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-26
"""

import sqlalchemy as sa
from alembic import op

from db import schema

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def bounded_columns(inspector: sa.Inspector, table: sa.Table, schema_name: str | None) -> list[str]:
    """Columns of `table` that the model declares as Text but the database still holds as a bounded varchar."""
    if table.name not in inspector.get_table_names(schema=schema_name):
        return []
    text_in_model = {c.name for c in table.columns if isinstance(c.type, sa.Text)}
    return [
        col["name"]
        for col in inspector.get_columns(table.name, schema=schema_name)
        if col["name"] in text_in_model and isinstance(col["type"], sa.String) and not isinstance(col["type"], sa.Text)
    ]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite ignores varchar lengths; nothing to widen
    inspector = sa.inspect(bind)
    for table in schema.MIRRORS.values():
        for name in bounded_columns(inspector, table, "nfl"):
            op.alter_column(table.name, name, type_=sa.Text(), schema="nfl")


def downgrade() -> None:
    # Narrowing back would truncate or reject real nflverse rows; text stays text.
    pass
