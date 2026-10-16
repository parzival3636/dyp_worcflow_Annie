"""
FastAPI application factory and lifespan configuration.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import init_db, get_db
from app.logging_config import setup_logging
from app.models.schemas import HealthResponse
from app.api.meetings import router as meetings_router
from app.api.webhooks import router as webhooks_router
from app.api.telegram import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    # Initialize database tables
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pilot Transcribe API",
        version="0.1.0",
        description="Meeting Link -> Transcript -> Proposed Tasks for Pilot",
        lifespan=lifespan,
    )

    # Health endpoint under /api/v1/transcribe
    @app.get("/api/v1/transcribe/health", response_model=HealthResponse)
    def health_check(db: Session = Depends(get_db)):
        # Verify db is reachable
        db_status = "ok"
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            db_status = "error"
        return HealthResponse(status="ok", db=db_status)

    # Include routers under /api/v1/transcribe prefix
    app.include_router(meetings_router, prefix="/api/v1/transcribe", tags=["meetings"])
    app.include_router(webhooks_router, prefix="/api/v1/transcribe", tags=["webhooks"])
    app.include_router(telegram_router, prefix="/api/v1/transcribe", tags=["telegram"])

    return app


app = create_app()
