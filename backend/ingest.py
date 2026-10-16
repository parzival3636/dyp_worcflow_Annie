"""
Pilot – group chat ingestion.

Cheap filter → debounce buffer → window builder → P3G → apply_observations.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

from sqlmodel import select, col
from telegram import Update
from telegram.ext import ContextTypes

from config import get_settings
from db import get_session
from models import Member, Message, Project, Task
from prompts import (
    P3G_SYSTEM, p3g_user_prompt, GroupExtraction,
)
from llm import call_json
from loop import apply_observations

logger = logging.getLogger("pilot.ingest")

# ── Per-group debounce buffers ─────────────────────────────────────────────

_buffers: dict[int, list[dict]] = defaultdict(list)   # group_id -> list of msg dicts
_last_msg_time: dict[int, float] = {}                  # group_id -> epoch
_flush_tasks: dict[int, asyncio.Task] = {}             # group_id -> scheduled flush
_queue: asyncio.Queue | None = None
_worker_task: asyncio.Task | None = None

# Work verbs for the cheap filter
_WORK_VERBS = re.compile(
    r"\b(done|pushed|merged|stuck|waiting|blocked|fixed|testing|deploy|deployed|"
    r"api|bug|ready|finished|complete|completed|shipped|reviewed|committed|"
    r"started|resolved|failed|broken|works|working|implemented|updated|refactored)\b",
    re.IGNORECASE,
)
_TASK_KEY_RE = re.compile(r"\bT-\d+\b", re.IGNORECASE)
_PURE_ACK = re.compile(r"^(ok|okay|hmm|hm|lol|lmao|haha|hehe|nice|cool|yep|yup|ya|k|kk|👍|😂|🔥|💯)\s*$", re.IGNORECASE)


def _cheap_filter(text: str, member_names: list[str], bot_username: str | None) -> bool:
    """
    Return True if the message should be KEPT for LLM processing.
    Skip: bot messages, stickers (handled before), commands, pure acks under 3 words.
    Keep: task keys, member names, @mentions, work verbs, replies to bot.
    """
    if not text or not text.strip():
        return False

    stripped = text.strip()

    # Skip commands
    if stripped.startswith("/"):
        return False

    # Skip pure acknowledgements under 3 words
    words = stripped.split()
    if len(words) <= 3 and _PURE_ACK.match(stripped):
        return False

    # Keep: task key mentioned
    if _TASK_KEY_RE.search(stripped):
        return True

    # Keep: work verbs
    if _WORK_VERBS.search(stripped):
        return True

    # Keep: member name or @mention
    lower = stripped.lower()
    for name in member_names:
        if name.lower() in lower:
            return True
    if "@" in stripped:
        return True

    # Keep: bot mentioned
    if bot_username and f"@{bot_username.lower()}" in lower:
        return True

    # Keep: messages over 10 words (might contain work context)
    if len(words) > 10:
        return True

    # Default: skip
    return False


# ── Message handling ───────────────────────────────────────────────────────

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process a text message from a linked group chat."""
    msg = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat_id
    tg_user = msg.from_user
    if not tg_user:
        return

    # Skip bot's own messages
    bot_user = await context.bot.get_me()
    if tg_user.id == bot_user.id:
        return

    text = msg.text

    # Find project for this group
    def _lookup():
        with get_session() as session:
            project = session.exec(
                select(Project).where(Project.telegram_group_id == chat_id)
            ).first()
            if not project:
                return None, None, []

            # Map sender to member
            member = session.exec(
                select(Member).where(
                    Member.project_id == project.id,
                    Member.telegram_id == tg_user.id,
                )
            ).first()

            # Get all member names for cheap filter
            members = session.exec(
                select(Member).where(Member.project_id == project.id)
            ).all()
            names = []
            for m in members:
                if m.name:
                    names.append(m.name)
                    # First name
                    names.append(m.name.split()[0])
                if isinstance(m.aliases, list):
                    names.extend(m.aliases)

            # Save message to DB (dedupe on chat_id + tg_message_id)
            existing = session.exec(
                select(Message).where(
                    Message.chat_id == chat_id,
                    Message.tg_message_id == msg.message_id,
                )
            ).first()
            if not existing:
                db_msg = Message(
                    project_id=project.id,
                    member_id=member.id if member else None,
                    direction="in",
                    text=text,
                    source="group",
                    chat_id=chat_id,
                    tg_message_id=msg.message_id,
                    reply_to_tg_message_id=msg.reply_to_message.message_id if msg.reply_to_message else None,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(db_msg)

            return (
                Project.model_validate(project),
                member.name if member else (tg_user.full_name or "Unknown"),
                names,
            )

    project, sender_name, member_names = await asyncio.to_thread(_lookup)
    if not project:
        return

    # Cheap filter
    bot_user = await context.bot.get_me()
    if not _cheap_filter(text, member_names, bot_user.username):
        return

    # Add to debounce buffer
    reply_to_name = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        reply_to_name = msg.reply_to_message.from_user.full_name

    msg_dict = {
        "text": text,
        "sender": sender_name,
        "time": datetime.now(timezone.utc).strftime("%H:%M"),
        "reply_to": reply_to_name,
        "tg_message_id": msg.message_id,
    }

    _buffers[chat_id].append(msg_dict)
    _last_msg_time[chat_id] = time.monotonic()

    settings = get_settings()

    # Check if buffer is full
    if len(_buffers[chat_id]) >= settings.group_max_buffer:
        await _flush_buffer(chat_id, project, context)
    else:
        # Schedule a debounced flush
        _schedule_flush(chat_id, project, context, settings.group_debounce_seconds)


async def handle_group_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle an edited message in a linked group chat."""
    msg = update.edited_message
    if not msg or not msg.text:
        return

    chat_id = msg.chat_id
    text = msg.text
    tg_user = msg.from_user
    if not tg_user:
        return

    # Update stored message and re-queue
    def _update():
        with get_session() as session:
            existing = session.exec(
                select(Message).where(
                    Message.chat_id == chat_id,
                    Message.tg_message_id == msg.message_id,
                )
            ).first()
            if existing:
                existing.text = text
                existing.processed = False
                session.add(existing)

            project = session.exec(
                select(Project).where(Project.telegram_group_id == chat_id)
            ).first()

            member = None
            if project:
                member = session.exec(
                    select(Member).where(
                        Member.project_id == project.id,
                        Member.telegram_id == tg_user.id,
                    )
                ).first()

            return (
                Project.model_validate(project) if project else None,
                member.name if member else (tg_user.full_name or "Unknown"),
            )

    project, sender_name = await asyncio.to_thread(_update)
    if not project:
        return

    # Re-queue the edited message through the same pipeline
    msg_dict = {
        "text": text,
        "sender": sender_name,
        "time": datetime.now(timezone.utc).strftime("%H:%M"),
        "reply_to": None,
        "tg_message_id": msg.message_id,
        "edited": True,
    }

    _buffers[chat_id].append(msg_dict)
    _last_msg_time[chat_id] = time.monotonic()

    settings = get_settings()
    if len(_buffers[chat_id]) >= settings.group_max_buffer:
        await _flush_buffer(chat_id, project, context)
    else:
        _schedule_flush(chat_id, project, context, settings.group_debounce_seconds)


def _schedule_flush(chat_id: int, project: Project, context, delay: float):
    """Schedule a debounced flush after `delay` seconds of quiet."""
    # Cancel any existing flush for this group
    if chat_id in _flush_tasks:
        _flush_tasks[chat_id].cancel()

    async def _delayed():
        await asyncio.sleep(delay)
        await _flush_buffer(chat_id, project, context)

    _flush_tasks[chat_id] = asyncio.create_task(_delayed())


async def _flush_buffer(chat_id: int, project: Project, context: ContextTypes.DEFAULT_TYPE):
    """Flush the debounce buffer: build window, call P3G, apply observations."""
    msgs = _buffers.pop(chat_id, [])
    if chat_id in _flush_tasks:
        _flush_tasks.pop(chat_id, None)

    if not msgs:
        return

    try:
        # Build context window: last 15 messages from DB
        def _build_window():
            with get_session() as session:
                recent = session.exec(
                    select(Message)
                    .where(
                        Message.chat_id == chat_id,
                        Message.source == "group",
                    )
                    .order_by(col(Message.created_at).desc())
                    .limit(15)  # type: ignore
                ).all()
                recent.reverse()  # oldest first

                # Get members and tasks
                members = session.exec(
                    select(Member).where(Member.project_id == project.id)
                ).all()
                tasks = session.exec(
                    select(Task).where(
                        Task.project_id == project.id,
                        col(Task.status).in_(["todo", "in_progress", "blocked", "claimed_done"]),
                    )
                ).all()

                member_data = []
                member_names_by_id = {}
                for m in members:
                    member_data.append({
                        "name": m.name or "Unknown",
                        "username": m.telegram_username or "",
                        "aliases": m.aliases if isinstance(m.aliases, list) else [],
                    })
                    member_names_by_id[m.id] = m.name or "Unknown"

                task_data = []
                for t in tasks:
                    owner_name = member_names_by_id.get(t.owner_member_id, "unassigned")
                    task_data.append({
                        "key": t.key,
                        "title": t.title or "",
                        "status": t.status,
                        "owner_name": owner_name,
                    })

                # Format messages
                formatted = []
                new_tg_ids = {m["tg_message_id"] for m in msgs}
                new_indices = []
                for i, db_msg in enumerate(recent):
                    sender = "Unknown"
                    if db_msg.member_id:
                        sender = member_names_by_id.get(db_msg.member_id, "Unknown")
                    reply_part = ""
                    if db_msg.reply_to_tg_message_id:
                        # Find the replied-to message sender
                        replied = session.exec(
                            select(Message).where(
                                Message.chat_id == chat_id,
                                Message.tg_message_id == db_msg.reply_to_tg_message_id,
                            )
                        ).first()
                        if replied and replied.member_id:
                            reply_part = f" (reply to {member_names_by_id.get(replied.member_id, '?')})"

                    line = f"[{db_msg.created_at.strftime('%H:%M') if db_msg.created_at else '??:??'}] <{sender}>: {db_msg.text or ''}{reply_part}"
                    formatted.append(line)
                    if db_msg.tg_message_id in new_tg_ids:
                        new_indices.append(i)

                return member_data, task_data, formatted, new_indices

        member_data, task_data, formatted_msgs, new_indices = await asyncio.to_thread(_build_window)

        if not formatted_msgs:
            return

        # Call P3G
        extraction = await call_json(
            P3G_SYSTEM,
            p3g_user_prompt(member_data, task_data, formatted_msgs, new_indices),
            GroupExtraction,
        )

        # Apply observations
        group_responses = await apply_observations(project, extraction)

        # Mark messages as processed
        def _mark_processed():
            with get_session() as session:
                for m in msgs:
                    db_msg = session.exec(
                        select(Message).where(
                            Message.chat_id == chat_id,
                            Message.tg_message_id == m["tg_message_id"],
                        )
                    ).first()
                    if db_msg:
                        db_msg.processed = True
                        session.add(db_msg)

        await asyncio.to_thread(_mark_processed)

        # Send group responses (only when needed: clarification, verdict, blocker routing)
        for resp in group_responses:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=resp,
                    parse_mode="Markdown",
                )
            except Exception:
                logger.exception("Failed to send group response")

        # Silent reaction on progress updates (thumbs up)
        for obs in extraction.observations:
            if obs.kind in ("progress", "completion_claim") and obs.confidence >= 0.6:
                for m in msgs:
                    if m["sender"] == obs.speaker:
                        try:
                            from telegram import ReactionTypeEmoji
                            await context.bot.set_message_reaction(
                                chat_id=chat_id,
                                message_id=m["tg_message_id"],
                                reaction=[ReactionTypeEmoji(emoji="👍")],
                            )
                        except Exception:
                            pass  # Reactions may not be available
                        break

    except Exception:
        logger.exception("_flush_buffer failed for chat %d", chat_id)
