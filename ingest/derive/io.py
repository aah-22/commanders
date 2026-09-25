"""Read a Core select into polars with dtypes taken from the table (an all-null column keeps its type)."""

from __future__ import annotations

import polars as pl
from sqlalchemy import Boolean, Float, Integer, Table
from sqlalchemy.engine import Connection


def dtype(col) -> type[pl.DataType]:  # noqa: ANN001
    if isinstance(col.type, Integer):
        return pl.Int64
    if isinstance(col.type, Float):
        return pl.Float64
    if isinstance(col.type, Boolean):
        return pl.Boolean
    return pl.Utf8


def frame(conn: Connection, stmt, table: Table) -> pl.DataFrame:  # noqa: ANN001
    rows = conn.execute(stmt).all()
    return pl.DataFrame(rows, schema=[(c.name, dtype(c)) for c in table.c], orient="row", strict=False)
