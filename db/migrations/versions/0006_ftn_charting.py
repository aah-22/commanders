"""explorer insights: nfl.ftn_charting mirror (FTN play charting, 2022 onwards)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-25
"""

from alembic import op

from db import schema

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

NEW_TABLES = ["ftn_charting"]


def _bind():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else bind.execution_options(**schema.sqlite_options())


def _tables():
    return [schema.metadata.tables[k] for k in schema.metadata.tables if k.split(".")[-1] in NEW_TABLES]


def upgrade() -> None:
    schema.metadata.create_all(bind=_bind(), tables=_tables())


def downgrade() -> None:
    schema.metadata.drop_all(bind=_bind(), tables=_tables())
