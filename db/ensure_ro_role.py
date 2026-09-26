"""Create or repair the API's read-only Postgres role at container start.  python -m db.ensure_ro_role

The role used to come from `db/init/01_roles.sql`, which Postgres only runs on a brand-new data directory and only
when the compose bind mount survives (Coolify drops it). Running this after `alembic upgrade head` makes a deploy
self-healing: the role named in DATABASE_URL_RO exists with that password, can connect, and has SELECT on every
table in the four schemas now and in the future. No-op outside Postgres (SQLite in tests / local dev).
"""

from __future__ import annotations

import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from db.schema import SCHEMAS

log = logging.getLogger("ensure_ro_role")


def statements(role: str, password: str, database: str, owner: str) -> list[str]:
    """The idempotent SQL as plain statements. DDL cannot take bind parameters, so identifiers are validated and the
    password is quoted as a SQL literal (single quotes doubled), which is the same escaping psql itself applies."""
    for ident in (role, database, owner):
        if not ident.replace("_", "").isalnum():
            raise ValueError(f"unsafe identifier {ident!r}")
    pw = "'" + password.replace("'", "''") + "'"
    out = [
        f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "  # noqa: S608  # nosec B608 - identifiers validated above
        f"CREATE ROLE {role} LOGIN; END IF; END $$",
        f"ALTER ROLE {role} LOGIN PASSWORD {pw}",
        f"GRANT CONNECT ON DATABASE {database} TO {role}",
    ]
    for s in SCHEMAS:
        out += [
            f"GRANT USAGE ON SCHEMA {s} TO {role}",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {s} TO {role}",
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {s} GRANT SELECT ON TABLES TO {role}",
        ]
    return out


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s %(message)s")
    owner_url = make_url(os.environ.get("DATABASE_URL", "sqlite:///./dev.db"))
    ro_url = make_url(os.environ.get("DATABASE_URL_RO", ""))
    if owner_url.get_backend_name() != "postgresql":
        log.info("not postgres, nothing to do")
        return 0
    if not ro_url.username or not ro_url.password:
        log.warning("DATABASE_URL_RO has no user/password, skipping")
        return 0
    eng = create_engine(owner_url, future=True)
    with eng.begin() as conn:
        for stmt in statements(ro_url.username, ro_url.password, owner_url.database, owner_url.username):
            conn.exec_driver_sql(stmt)
    log.info("role %s ready on %s", ro_url.username, owner_url.database)
    return 0


if __name__ == "__main__":
    sys.exit(main())
