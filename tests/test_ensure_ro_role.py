"""The startup role repair: idempotent SQL for Postgres, a no-op elsewhere."""

import pytest

from db import ensure_ro_role


def test_statements_create_grant_and_cover_every_schema():
    stmts = ensure_ro_role.statements("commanders_ro", "s3c'ret", "commanders", "commanders")
    assert "CREATE ROLE commanders_ro LOGIN" in stmts[0] and "IF NOT EXISTS" in stmts[0]
    assert stmts[1] == "ALTER ROLE commanders_ro LOGIN PASSWORD 's3c''ret'"  # quote doubled, literal closed
    for s in ("nfl", "gm", "ml", "ops"):
        assert f"GRANT SELECT ON ALL TABLES IN SCHEMA {s} TO commanders_ro" in stmts
        assert (
            f"ALTER DEFAULT PRIVILEGES FOR ROLE commanders IN SCHEMA {s} GRANT SELECT ON TABLES TO commanders_ro"
            in stmts
        )


def test_identifiers_are_validated():
    with pytest.raises(ValueError):
        ensure_ro_role.statements("ro; DROP ROLE x", "pw", "commanders", "commanders")


def test_noop_on_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")
    monkeypatch.setenv("DATABASE_URL_RO", f"sqlite:///{tmp_path / 'x.db'}")
    assert ensure_ro_role.main() == 0
