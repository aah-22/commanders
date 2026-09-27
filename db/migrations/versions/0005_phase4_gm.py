"""phase 4: gm.player_season_production, gm.acquisitions, gm.positional_need and ml.model_outputs

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27
"""

from alembic import op

from db import schema

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

NEW_TABLES = ["player_season_production", "acquisitions", "positional_need", "model_outputs"]


def _bind():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else bind.execution_options(**schema.sqlite_options())


def _tables():
    return [schema.metadata.tables[k] for k in schema.metadata.tables if k.split(".")[-1] in NEW_TABLES]


def upgrade() -> None:
    schema.metadata.create_all(bind=_bind(), tables=_tables())


def downgrade() -> None:
    schema.metadata.drop_all(bind=_bind(), tables=_tables())
