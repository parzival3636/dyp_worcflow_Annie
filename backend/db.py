"""
Pilot – database engine and session helper.

Connects DIRECTLY to Supabase Postgres using DATABASE_URL.
We use the SESSION pooler (port 5432) which supports prepared statements
and persistent connections. Alembic manages the schema; no create_all() here.

Connection strategy: Session pooler (port 5432, sslmode=require)
- Supports prepared statements (no statement_cache_size=0 workaround needed)
- pool_size=5 + max_overflow=5: shared between bot, scheduler, verifier, API
- pool_pre_ping=True: recycles stale connections gracefully
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, create_engine

from config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if "postgres" in settings.database_url:
            connect_args["connect_timeout"] = 5
        _engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            # Supabase session pooler (port 5432) supports prepared statements natively
        )
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional session. Commits on success, rolls back on error."""
    engine = get_engine()
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
