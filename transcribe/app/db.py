"""
Database engine and session management.
SQLAlchemy 2.0+ declarative base and session factory.
"""
from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import get_settings

Base = declarative_base()

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            echo=False,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI route handlers."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def init_db(engine=None):
    """Create all tables."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
