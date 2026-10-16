"""
Pilot – database engine and session helper.

Uses SQLModel + psycopg (v3) against Supabase Postgres.
Sync sessions are run from async handlers via asyncio.to_thread.
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
        if settings.database_url.startswith("sqlite"):
            _engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
            )
        from models import SQLModel
        SQLModel.metadata.create_all(_engine)
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
