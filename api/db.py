"""SQLAlchemy engine/session for the API (read-only role). Jobs use db.session.job_engine with the owner URL."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from api.config import get_settings

_engine = None
_Session = None


def engine():
    global _engine, _Session
    if _engine is None:
        url = get_settings().database_url_ro
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Iterator[Session]:
    engine()
    with _Session() as s:
        yield s


def ping() -> bool:
    try:
        with engine().connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
