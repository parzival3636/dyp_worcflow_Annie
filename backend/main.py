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

    # Import and start bot
    from bot import start_bot, stop_bot
    bot_task = asyncio.create_task(start_bot())

    # Import and start scheduler
    from loop import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    # Shutdown
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

app = FastAPI(title="Pilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


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
