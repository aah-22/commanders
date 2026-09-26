"""nflverse mirrors never bound their text columns (migration 0004); the widening step finds exactly the varchar ones."""

import importlib

import sqlalchemy as sa

from db import schema

widen = importlib.import_module("db.migrations.versions.0004_widen_mirror_text")


def test_mirror_tables_declare_only_unbounded_text():
    bounded = [
        f"{t.name}.{c.name}"
        for t in schema.MIRRORS.values()
        for c in t.columns
        if isinstance(c.type, sa.String) and not isinstance(c.type, sa.Text)
    ]
    assert bounded == []


def test_bounded_columns_reports_varchar_columns_the_model_calls_text(tmp_path):
    """A database created from the pre-0004 model (bounded varchars) is what the migration has to widen."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    old = sa.MetaData()
    sa.Table(
        "players",
        old,
        sa.Column("gsis_id", sa.String(16), primary_key=True),
        sa.Column("college_name", sa.String(64)),
        sa.Column("headshot", sa.Text),
        sa.Column("height", sa.Float),
    )
    old.create_all(engine)
    with engine.connect() as conn:
        names = widen.bounded_columns(sa.inspect(conn), schema.MIRRORS["players"], None)
    assert names == ["gsis_id", "college_name"]


def test_bounded_columns_is_empty_for_a_fresh_database(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    with engine.connect() as conn:
        conn = conn.execution_options(**schema.sqlite_options())
        schema.MIRRORS["players"].create(conn)
        assert widen.bounded_columns(sa.inspect(conn), schema.MIRRORS["players"], None) == []
        assert widen.bounded_columns(sa.inspect(conn), schema.MIRRORS["contracts"], None) == []  # table absent
