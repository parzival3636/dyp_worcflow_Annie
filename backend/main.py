"""
Pilot – FastAPI entrypoint.

Lifespan starts the Telegram bot (long polling) and APScheduler,
then shuts them down on exit.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import get_settings
from db import get_engine, get_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pilot")


# ── health probes ──────────────────────────────────────────────────────────

def _check_db() -> str:
    try:
        from sqlmodel import text
        with get_session() as session:
            session.exec(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


async def _check_llm() -> str:
    try:
        import httpx
        settings = get_settings()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.llm_base_url}/models",
                                    headers={"Authorization": f"Bearer {settings.llm_api_key}"})
            if resp.status_code < 400:
                return "ok"
            return f"error: HTTP {resp.status_code}"
    except Exception as exc:
        return f"error: {exc}"


def _check_telegram() -> str:
    """Returns ok if the bot application is running."""
    try:
        from bot import _bot_app
        if _bot_app and _bot_app.updater and _bot_app.updater.running:
            return "ok"
        if _bot_app is not None:
            return "ok"  # app exists, may just not expose .running in v21
        return "error: not running"
    except Exception as exc:
        return f"error: {exc}"


# ── lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the Telegram bot and scheduler; tear down on shutdown."""
    settings = get_settings()
    logger.info("Pilot starting (demo_mode=%s)", settings.demo_mode)

    # Ensure engine is initialised (validates DB URL early)
    get_engine()

    # Initialize transcribe tables if transcribe package present
    try:
        import sys
        from pathlib import Path
        root_dir = Path(__file__).resolve().parent.parent
        transcribe_dir = root_dir / "transcribe"
        if str(transcribe_dir) not in sys.path:
            sys.path.insert(0, str(transcribe_dir))
        from app.db import init_db as init_transcribe_db
        init_transcribe_db()
        logger.info("Transcribe database tables initialized")
    except Exception as exc:
        logger.warning("Could not initialize transcribe DB: %s", exc)

    # Import and start bot
    from bot import start_bot, stop_bot
    bot_task = asyncio.create_task(start_bot())

    # Import and start scheduler
    from loop import start_scheduler, stop_scheduler
    start_scheduler()

    # Import and start Annie webhook worker
    try:
        from annie import WebhookWorker
        annie_worker = WebhookWorker()
        annie_task = asyncio.create_task(annie_worker.start())
        logger.info("Annie verification worker initialized & running")
    except Exception as exc:
        annie_worker = None
        annie_task = None
        logger.warning("Could not start Annie webhook worker: %s", exc)

    yield

    # Shutdown
    if annie_worker:
        annie_worker.stop()
    if annie_task:
        annie_task.cancel()
        try:
            await annie_task
        except asyncio.CancelledError:
            pass

    stop_scheduler()
    await stop_bot()
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    logger.info("Pilot stopped")


# ── FastAPI app ────────────────────────────────────────────────────────────

from fastapi.middleware.cors import CORSMiddleware
from routes import router as api_router
from auth_routes import router as auth_router

app = FastAPI(title="Pilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")

# Mount Annie verification & GitHub endpoints
try:
    from annie import repos_router, tasks_router, dashboard_router
    # Root paths for Annie frontend
    app.include_router(repos_router)
    app.include_router(tasks_router)
    app.include_router(dashboard_router)
    # /api prefixed paths for unified routing
    app.include_router(repos_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    logger.info("Mounted Annie GitHub & verification routers at / and /api")
except Exception as exc:
    logger.warning("Could not mount Annie routers: %s", exc)


# Mount Transcribe API endpoints
try:
    import sys
    from pathlib import Path
    root_dir = Path(__file__).resolve().parent.parent
    transcribe_dir = root_dir / "transcribe"
    if str(transcribe_dir) not in sys.path:
        sys.path.insert(0, str(transcribe_dir))

    from app.api.meetings import router as transcribe_meetings_router
    from app.api.webhooks import router as transcribe_webhooks_router
    from app.api.telegram import router as transcribe_telegram_router

    app.include_router(transcribe_meetings_router, prefix="/api/v1/transcribe", tags=["transcribe-meetings"])
    app.include_router(transcribe_webhooks_router, prefix="/api/v1/transcribe", tags=["transcribe-webhooks"])
    app.include_router(transcribe_telegram_router, prefix="/api/v1/transcribe", tags=["transcribe-telegram"])

    app.include_router(transcribe_meetings_router, prefix="/api/transcribe", tags=["transcribe-meetings"])
    app.include_router(transcribe_webhooks_router, prefix="/api/transcribe", tags=["transcribe-webhooks"])
    app.include_router(transcribe_telegram_router, prefix="/api/transcribe", tags=["transcribe-telegram"])
    logger.info("Mounted transcribe API endpoints under /api/v1/transcribe and /api/transcribe")
except Exception as exc:
    logger.warning("Could not mount transcribe routers: %s", exc)


@app.get("/api/health")
async def health():
    db_status = await asyncio.to_thread(_check_db)
    llm_status = await _check_llm()
    tg_status = _check_telegram()
    return JSONResponse({
        "db": db_status,
        "llm": llm_status,
        "telegram": tg_status,
    })


@app.post("/api/projects/{code}/followup")
async def api_followup(code: str):
    """Trigger an immediate check-in cycle for the given project."""
    from loop import checkin_tick
    await checkin_tick()
    return JSONResponse({"status": "ok", "detail": "Check-in cycle triggered"})


@app.post("/api/projects/{code}/inject_reply")
async def api_inject_reply(code: str, body: dict):
    """
    Run text through the DM reply handler as if a member sent it.
    Body: {member_id: int, text: str}
    The bot's response is still sent over real Telegram.
    """
    from sqlmodel import select
    from models import Member, Project
    from loop import handle_dm_reply
    from bot import _bot_app

    member_id = body.get("member_id")
    text = body.get("text", "")

    if not member_id or not text:
        return JSONResponse({"error": "member_id and text are required"}, status_code=400)

    def _lookup():
        with get_session() as session:
            project = session.exec(
                select(Project).where(Project.code == code)
            ).first()
            member = session.get(Member, member_id)
            return (
                Project.model_validate(project) if project else None,
                Member.model_validate(member) if member else None,
            )

    project, member = await asyncio.to_thread(_lookup)

    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)
    if not member:
        return JSONResponse({"error": "Member not found"}, status_code=404)

    responses = await handle_dm_reply(
        member=member,
        message_text=text,
        project=project,
    )

    # Send responses over Telegram if the member has a telegram_id
    if _bot_app and member.telegram_id:
        for resp in responses:
            try:
                await _bot_app.bot.send_message(
                    chat_id=member.telegram_id,
                    text=resp,
                    parse_mode="Markdown",
                )
            except Exception:
                logger.warning("Failed to send injected reply to Telegram")

    return JSONResponse({"status": "ok", "responses": responses})
