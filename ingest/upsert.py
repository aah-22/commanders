"""Idempotent bulk upserts: polars → Postgres `INSERT … ON CONFLICT DO UPDATE` (SQLite falls back to INSERT OR REPLACE
for the tests). Every mirror table is written this way, so re-running a job on unchanged data changes nothing."""

from __future__ import annotations

import math
from collections.abc import Iterable

import polars as pl
from sqlalchemy import Table, inspect
from sqlalchemy.engine import Connection

CHUNK = 5000


def _records(df: pl.DataFrame, columns: list[str]) -> Iterable[dict]:
    for row in df.select(columns).iter_rows(named=True):
        yield {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}


def upsert(conn: Connection, table: Table, df: pl.DataFrame, key: list[str]) -> int:
    """Write df into table on its natural key; returns the number of rows sent. Columns not in the table are dropped,
    table columns absent from df are left untouched on update (they keep their value) and NULL on insert."""
    cols = [c for c in df.columns if c in table.c]
    if not cols or df.is_empty():
        return 0
    df = df.unique(subset=key, keep="last", maintain_order=True)
    dialect = conn.dialect.name
    n = 0
    for start in range(0, df.height, CHUNK):
        rows = list(_records(df.slice(start, CHUNK), cols))
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert

            stmt = insert(table).values(rows)
            update = {c: stmt.excluded[c] for c in cols if c not in key}
            stmt = (
                stmt.on_conflict_do_update(index_elements=key, set_=update)
                if update
                else stmt.on_conflict_do_nothing(index_elements=key)
            )
        else:
            from sqlalchemy.dialects.sqlite import insert

            stmt = insert(table).values(rows)
            update = {c: stmt.excluded[c] for c in cols if c not in key}
            stmt = (
                stmt.on_conflict_do_update(index_elements=key, set_=update)
                if update
                else stmt.on_conflict_do_nothing(index_elements=key)
            )
        conn.execute(stmt)
        n += len(rows)
    return n


def table_for(conn: Connection, name: str, metadata) -> Table:
    """The ORM table by bare name, whatever schema the dialect put it in (Postgres schemas, SQLite plain tables)."""
    for t in metadata.tables.values():
        if t.name == name:
            return t
    raise KeyError(name)


def has_table(conn: Connection, name: str, schema: str | None) -> bool:
    return inspect(conn).has_table(name, schema=schema)
