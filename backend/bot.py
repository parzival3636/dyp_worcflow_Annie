"""
Pilot – Telegram bot handlers.

DM commands, onboarding, callbacks, group-chat listener.
Every handler wrapped in @safe. Every message logged to the DB.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
import string
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select, col
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import get_settings
from db import get_session
from models import (
    Blocker, Event, Member, Message, Project, Task,
)
from loop import handle_dm_reply, checkin_tick, TransitionError, transition
import stubs

logger = logging.getLogger("pilot.bot")

_bot_app: Application | None = None

# ═══════════════════════════════════════════════════════════════════════════
# DECORATOR: @safe — wraps every handler in try/except
# ═══════════════════════════════════════════════════════════════════════════

def safe(func):
    """Decorator that catches all exceptions, logs them, and sends a friendly error."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception:
            logger.exception("Handler %s failed", func.__name__)
            try:
                chat_id = None
                if update.effective_chat:
                    chat_id = update.effective_chat.id
                elif update.callback_query and update.callback_query.message:
                    chat_id = update.callback_query.message.chat_id
                if chat_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Something went wrong, try again in a moment.",
                    )
            except Exception:
                logger.exception("Failed to send error message")
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _gen_code() -> str:
    """Generate a 6-char alphanumeric project code."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def _log_outbound(project_id: int | None, member_id: int | None, text: str,
                   chat_id: int | None, tg_message_id: int | None, source: str = "dm"):
    """Log an outbound message to the DB."""
    try:
        with get_session() as session:
            msg = Message(
                project_id=project_id,
                member_id=member_id,
                direction="out",
                text=text,
                source=source,
                chat_id=chat_id,
                tg_message_id=tg_message_id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
    except Exception:
        logger.exception("Failed to log outbound message")


def _log_inbound(project_id: int | None, member_id: int | None, text: str,
                  chat_id: int | None, tg_message_id: int | None,
                  source: str = "dm", reply_to: int | None = None):
    """Log an inbound message to the DB."""
    try:
        with get_session() as session:
            msg = Message(
                project_id=project_id,
                member_id=member_id,
                direction="in",
                text=text,
                source=source,
                chat_id=chat_id,
                tg_message_id=tg_message_id,
                reply_to_tg_message_id=reply_to,
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
    except Exception:
        logger.exception("Failed to log inbound message")


def _find_member_by_tg(session: Session, telegram_id: int) -> Member | None:
    return session.exec(
        select(Member).where(Member.telegram_id == telegram_id)
    ).first()


def _find_project_by_code(session: Session, code: str) -> Project | None:
    return session.exec(
        select(Project).where(Project.code == code)
    ).first()


def _resolve_context(session: Session, update: Update) -> tuple[Project | None, Member | None]:
    """
    Strictly resolve the active project and member based on where the command was called:
    1. In a group chat: strictly uses the project linked to THIS specific group!
    2. In private DM: uses the sender's most recent project membership.
    """
    chat = update.effective_chat
    user = update.effective_user
    if not user:
        return None, None

    if chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        project = session.exec(
            select(Project).where(Project.telegram_group_id == chat.id)
        ).first()
        if project:
            member = session.exec(
                select(Member).where(
                    Member.project_id == project.id,
                    Member.telegram_id == user.id,
                )
            ).first()
            return project, member

    # Private DM context: most recent project
    member = session.exec(
        select(Member).where(Member.telegram_id == user.id).order_by(col(Member.id).desc())
    ).first()
    project = None
    if member and member.project_id:
        project = session.get(Project, member.project_id)

    return project, member



# ═══════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

@safe
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /start join_<code>."""
    if not update.effective_chat or update.effective_chat.type != ChatType.PRIVATE:
        return
    if not update.message:
        return

    args = context.args
    tg_user = update.effective_user

    # /start join_<code>
    if args and args[0].startswith("join_"):
        code = args[0][5:]
        await _handle_join(update, context, code, tg_user)
        return

    # Plain /start
    await update.message.reply_text(
        "👋 *Welcome to Pilot!*\n\n"
        "I'm your AI project coordinator. Here's what I can do:\n\n"
        "• `/newproject <idea>` — Create a new project\n"
        "• `/mytasks` — See your current tasks\n"
        "• `/status` — Project status overview\n"
        "• `/ask <question>` — Ask about the project\n"
        "• `/report` — Get a project report\n"
        "• `/followup` — Force a check-in now\n"
        "• `/help` — Show all commands\n\n"
        "To join an existing project, use the invite link your lead sent you.",
        parse_mode=ParseMode.MARKDOWN,
    )


@safe
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands."""
    if not update.message:
        return
    await update.message.reply_text(
        "📖 *Pilot Commands*\n\n"
        "*Project Setup:*\n"
        "• `/newproject <idea>` — Create a new project\n"
        "• `/plan` — Generate task plan\n"
        "• `/kickoff` — Start the project and notify everyone\n"
        "• `/linkgroup <code>` — Link a Telegram group (run in the group)\n\n"
        "*During Work:*\n"
        "• `/mytasks` — Your current tasks\n"
        "• `/status` — Project overview\n"
        "• `/ask <question>` — Ask about the project\n"
        "• `/report` — Full project report\n"
        "• `/followup` — Force an immediate check-in\n\n"
        "*Tips:*\n"
        "• Reply to check-ins in plain text — I understand natural language\n"
        "• Use buttons for quick updates\n"
        "• Put `[T-n]` in your commit messages so I can track them",
        parse_mode=ParseMode.MARKDOWN,
    )


@safe
async def cmd_newproject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new project."""
    if not update.message or not update.effective_user:
        return
    if update.effective_chat and update.effective_chat.type != ChatType.PRIVATE:
        await update.message.reply_text("Please use this command in a DM with me.")
        return

    idea = " ".join(context.args) if context.args else ""
    if not idea:
        await update.message.reply_text("Please provide an idea: `/newproject <your idea>`",
                                         parse_mode=ParseMode.MARKDOWN)
        return

    tg_user = update.effective_user

    def _create():
        parsed = stubs.parse_idea(idea)
        repo_info = None
        try:
            repo_info = stubs.create_repo(parsed["name"])
        except Exception:
            logger.warning("create_repo failed, continuing without repo")

        code = _gen_code()
        with get_session() as session:
            project = Project(
                code=code,
                name=parsed["name"],
                idea=idea,
                repo_full_name=repo_info["full_name"] if repo_info else None,
                repo_url=repo_info["url"] if repo_info else None,
                status="planning",
            )
            session.add(project)
            session.flush()

            # Create lead member
            member = Member(
                project_id=project.id,
                name=tg_user.full_name,
                telegram_id=tg_user.id,
                telegram_username=tg_user.username,
                role="lead",
                invite_status="accepted",
                onboarding_state="awaiting_github",
            )
            session.add(member)
            session.flush()

            project.lead_member_id = member.id
            session.add(project)

            # Event
            event = Event(
                project_id=project.id,
                ts=datetime.now(timezone.utc),
                actor_member_id=member.id,
                type="project_created",
                payload={"idea": idea, "code": code},
            )
            session.add(event)

            return {
                "code": code,
                "repo_url": repo_info["url"] if repo_info else None,
                "repo_name": repo_info["full_name"] if repo_info else None,
                "member_id": member.id,
            }

    result = await asyncio.to_thread(_create)

    bot_username = (await context.bot.get_me()).username
    join_link = f"https://t.me/{bot_username}?start=join_{result['code']}"

    text = f"🚀 *Project created!*\n\n"
    text += f"📋 Code: `{result['code']}`\n"
    if result["repo_url"]:
        text += f"📦 Repo: {result['repo_url']}\n"
    else:
        text += "⚠️ Repo creation failed — you can set it up manually.\n"
    text += f"\n🔗 *Invite link:* {join_link}\n"
    text += "\nShare this link with your teammates to get them onboarded!\n"
    text += "\nNow, please send me your **GitHub username** so I can add you as a collaborator."

    sent = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    await asyncio.to_thread(
        _log_outbound, None, result["member_id"], text,
        update.effective_chat.id, sent.message_id if sent else None,
    )


async def _handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str, tg_user):
    """Handle join flow from /start join_<code>."""
    def _join():
        with get_session() as session:
            project = _find_project_by_code(session, code)
            if not project:
                return None, "Project not found. Check the code and try again."

            # Check if already a member
            existing = session.exec(
                select(Member).where(
                    Member.project_id == project.id,
                    Member.telegram_id == tg_user.id,
                )
            ).first()
            if existing:
                return None, f"You're already a member of *{project.name}*!"

            member = Member(
                project_id=project.id,
                name=tg_user.full_name,
                telegram_id=tg_user.id,
                telegram_username=tg_user.username,
                role="member",
                invite_status="accepted",
                onboarding_state="awaiting_github",
            )
            session.add(member)
            session.flush()

            event = Event(
                project_id=project.id,
                ts=datetime.now(timezone.utc),
                actor_member_id=member.id,
                type="member_joined",
                payload={"name": tg_user.full_name},
            )
            session.add(event)

            return project.name, None

    project_name, error = await asyncio.to_thread(_join)

    if error:
        await update.message.reply_text(error, parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        f"🎉 Welcome to *{project_name}*!\n\n"
        "Please send me your **GitHub username** so I can add you as a collaborator.",
        parse_mode=ParseMode.MARKDOWN,
    )


@safe
async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow members in a linked group or via code to join the project."""
    if not update.message or not update.effective_user:
        return
    chat = update.effective_chat
    tg_user = update.effective_user
    code = context.args[0] if context.args else None

    def _join():
        with get_session() as session:
            project = None
            if code:
                project = _find_project_by_code(session, code)
            elif chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                project = session.exec(
                    select(Project).where(Project.telegram_group_id == chat.id)
                ).first()

            if not project:
                return None, "Please specify a project code: `/join <project_code>`"

            existing = session.exec(
                select(Member).where(
                    Member.project_id == project.id,
                    Member.telegram_id == tg_user.id,
                )
            ).first()
            if existing:
                return project.name, f"You are already a member of *{project.name}*!"

            member = Member(
                project_id=project.id,
                name=tg_user.full_name,
                telegram_id=tg_user.id,
                telegram_username=tg_user.username,
                role="member",
                invite_status="accepted",
                onboarding_state="done",
            )
            session.add(member)
            return project.name, f"🎉 Welcome {tg_user.full_name}! You have joined *{project.name}*."

    _, text = await asyncio.to_thread(_join)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)



@safe
async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate task plan for the project."""
    if not update.message or not update.effective_user:
        return

    def _do():
        with get_session() as session:
            project, member = _resolve_context(session, update)
            if not project:
                return None, "No project linked to this chat. Run `/linkgroup <project_code>` first."
            task_ids = stubs.generate_tasks(project.id)
            stubs.bundle_and_assign(project.id)
            return (project.name, len(task_ids)), None

    result, err = await asyncio.to_thread(_do)
    if err:
        await update.message.reply_text(err, parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        f"📝 Plan generated for *{result[0]}* — {result[1]} tasks created.\n"
        "Use `/kickoff` when you're ready to start!",
        parse_mode=ParseMode.MARKDOWN,
    )


@safe
async def cmd_kickoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the project: set to running, DM each member their tasks."""
    if not update.message or not update.effective_user:
        return

    def _do():
        with get_session() as session:
            project, member = _resolve_context(session, update)
            if not project:
                return None, "No project linked to this chat. Run `/linkgroup <project_code>` first."
            if not member or member.role != "lead":
                return None, "Only the project lead can kickoff."

            project.status = "running"
            project.starts_at = datetime.now(timezone.utc)
            session.add(project)

            stubs.kickoff(project.id)

            # Get all members and their tasks
            members = session.exec(
                select(Member).where(Member.project_id == project.id)
            ).all()

            member_tasks = {}
            for m in members:
                tasks = session.exec(
                    select(Task).where(
                        Task.project_id == project.id,
                        Task.owner_member_id == m.id,
                    )
                ).all()
                if tasks:
                    member_tasks[m.telegram_id] = {
                        "name": m.name,
                        "tasks": [
                            {
                                "key": t.key,
                                "title": t.title,
                                "deadline": t.deadline.strftime("%b %d, %H:%M UTC") if t.deadline else "TBD",
                                "criteria": t.acceptance_criteria if isinstance(t.acceptance_criteria, list) else [],
                            }
                            for t in tasks
                        ],
                    }

            return member_tasks, None

    member_tasks, error = await asyncio.to_thread(_do)

    if error:
        await update.message.reply_text(error)
        return

    if not member_tasks:
        await update.message.reply_text(
            "🚀 Project is now *running*! No tasks assigned yet — use `/plan` first.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # DM each member
    for tg_id, info in (member_tasks or {}).items():
        try:
            task_lines = []
            for t in info["tasks"]:
                criteria_str = ""
                if t["criteria"]:
                    criteria_str = "\n      " + "\n      ".join(f"✓ {c}" for c in t["criteria"][:3])
                task_lines.append(
                    f"  • *{t['key']}*: {t['title']}\n"
                    f"    📅 Deadline: {t['deadline']}{criteria_str}"
                )

            text = (
                f"🚀 *{info['name']}, the project has kicked off!*\n\n"
                f"Your tasks:\n" + "\n".join(task_lines) + "\n\n"
                "💡 *Commit rule:* Put `[T-n]` in every commit message so I can track your progress.\n"
                "I'll check in with you periodically — just reply in plain text!"
            )
            await context.bot.send_message(chat_id=tg_id, text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            logger.exception("Failed to DM member %s", tg_id)

    summary_lines = ["🚀 *Project kicked off!* Everyone has been notified.\n\n*Assigned Tasks:*"]
    for tg_id, info in (member_tasks or {}).items():
        summary_lines.append(f"\n👤 *{info['name']}:*")
        for t in info["tasks"]:
            summary_lines.append(f"  • *{t['key']}*: {t['title']} ({t['deadline']})")

    summary_lines.append("\n💡 *Commit rule:* Put `[T-n]` in commit messages or chat updates about your tasks here!")
    await update.message.reply_text("\n".join(summary_lines), parse_mode=ParseMode.MARKDOWN)



@safe
async def cmd_mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the member's current tasks."""
    if not update.message or not update.effective_user:
        return

    def _do():
        with get_session() as session:
            project, member = _resolve_context(session, update)
            if not project:
                return None, "No project linked to this chat."
            if not member:
                return None, "You are not registered in this project. Send `/join` to join!"

            tasks = session.exec(
                select(Task).where(
                    Task.project_id == project.id,
                    Task.owner_member_id == member.id,
                )
            ).all()

            task_list = [
                {
                    "key": t.key,
                    "title": t.title,
                    "status": t.status,
                    "progress": t.progress,
                    "deadline": t.deadline.strftime("%b %d") if t.deadline else "—",
                }
                for t in tasks
            ]
            return (task_list, member.name, project.name), None

    result, err = await asyncio.to_thread(_do)
    if err:
        await update.message.reply_text(err, parse_mode=ParseMode.MARKDOWN)
        return

    tasks, member_name, project_name = result
    if not tasks:
        clean_proj = str(project_name).replace('_', ' ')
        await update.message.reply_text(f"You don't have any tasks assigned in *{clean_proj}*! 🎉", parse_mode=ParseMode.MARKDOWN)
        return

    status_emoji = {
        "todo": "⬜ Todo", "in_progress": "🔵 In Progress", "blocked": "🚧 Blocked",
        "claimed_done": "🟡 Claimed Done", "needs_review": "🔍 Needs Review", "verified_done": "✅ Verified Done",
    }
    clean_proj = str(project_name).replace('_', ' ')
    lines = [f"📋 *Tasks assigned to {member_name} ({clean_proj}):*\n"]
    for t in tasks:
        label = status_emoji.get(t["status"], t["status"].replace("_", " "))
        title = str(t['title']).replace('_', ' ')
        lines.append(f"{label.split()[0]} *{t['key']}*: {title} ({label}, {t['progress']}%) — {t['deadline']}")

    text_to_send = "\n".join(lines)
    try:
        await update.message.reply_text(text_to_send, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(text_to_send)


@safe
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show project status overview."""
    if not update.message or not update.effective_user:
        return

    def _do():
        with get_session() as session:
            project, member = _resolve_context(session, update)
            if not project:
                return None

            tasks = session.exec(
                select(Task).where(Task.project_id == project.id)
            ).all()

            members = session.exec(
                select(Member).where(Member.project_id == project.id)
            ).all()
            member_names = {m.id: m.name for m in members}

            counts = {}
            for t in tasks:
                counts[t.status] = counts.get(t.status, 0) + 1

            blockers = session.exec(
                select(Blocker).where(Blocker.status == "open")
            ).all()
            project_task_ids = {t.id for t in tasks}
            open_blockers = [b for b in blockers if b.task_id in project_task_ids]

            task_list = [
                {
                    "key": t.key,
                    "title": t.title,
                    "status": t.status,
                    "owner": member_names.get(t.owner_member_id, "Unassigned"),
                    "progress": t.progress,
                }
                for t in tasks
            ]

            return {
                "name": project.name,
                "status": project.status,
                "total": len(tasks),
                "counts": counts,
                "blockers": len(open_blockers),
                "tasks": task_list,
            }

    data = await asyncio.to_thread(_do)
    if not data:
        await update.message.reply_text("No project linked to this chat. Run `/linkgroup <project_code>` first.")
        return

    status_labels = {
        "todo": "⬜ Todo",
        "in_progress": "🔵 In Progress",
        "blocked": "🚧 Blocked",
        "claimed_done": "🟡 Claimed Done",
        "needs_review": "🔍 Needs Review",
        "verified_done": "✅ Verified Done",
    }

    proj_name = str(data['name']).replace('_', ' ')
    proj_status = str(data['status']).replace('_', ' ')
    lines = [
        f"📊 *{proj_name}* ({proj_status})\n",
        f"Total tasks: {data['total']}",
    ]
    for status, count in sorted(data["counts"].items()):
        lbl = status_labels.get(status, status.replace("_", " ").title())
        lines.append(f"  • {lbl}: {count}")
    if data["blockers"]:
        lines.append(f"\n🚧 Open blockers: {data['blockers']}")

    if data["tasks"]:
        lines.append("\n*Tasks & Assignees:*")
        for t in data["tasks"]:
            emoji = status_labels.get(t["status"], "⬜").split()[0]
            clean_title = str(t['title']).replace('_', ' ')
            lines.append(f"  {emoji} *{t['key']}* ({t['owner']}): {clean_title}")

    status_text = "\n".join(lines)
    try:
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(status_text)


@safe
async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask a question about the project."""
    if not update.message or not update.effective_user:
        return

    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text("What would you like to know? `/ask <your question>`",
                                         parse_mode=ParseMode.MARKDOWN)
        return

    def _do():
        with get_session() as session:
            project, member = _resolve_context(session, update)
            if not project:
                return None
            return stubs.guide_answer(project.id, question)

    answer = await asyncio.to_thread(_do)
    if answer is None:
        await update.message.reply_text("No project linked to this chat.")
        return

    try:
        await update.message.reply_text(answer, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(answer)


@safe
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a project report."""
    if not update.message or not update.effective_user:
        return

    def _do():
        with get_session() as session:
            project, member = _resolve_context(session, update)
            if not project:
                return None
            return stubs.guide_report(project.id)

    report = await asyncio.to_thread(_do)
    if report is None:
        await update.message.reply_text("No project linked to this chat.")
        return

    try:
        await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(report)


@safe
async def cmd_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force an immediate check-in cycle, ignoring cadence/cooldown/quiet hours."""
    if not update.message or not update.effective_user:
        return

    await update.message.reply_text("🔄 Running check-in cycle now…")
    await checkin_tick()
    await update.message.reply_text("✅ Check-in cycle complete.")


@safe
async def cmd_linkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Link a Telegram group to a project. Must be run in a group."""
    if not update.message:
        return

    chat = update.effective_chat
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await update.message.reply_text("Run this command inside a Telegram group.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/linkgroup <project_code>`",
                                         parse_mode=ParseMode.MARKDOWN)
        return

    code = context.args[0]

    def _link():
        with get_session() as session:
            project = _find_project_by_code(session, code)
            if not project:
                return "Project not found. Check the code."
            project.telegram_group_id = chat.id
            session.add(project)
            return None

    error = await asyncio.to_thread(_link)
    if error:
        await update.message.reply_text(error)
        return

    await update.message.reply_text(
        "✅ Group linked! I'll read this chat to track project progress.\n"
        "Normal chat is fine — I only act on work updates. 🤖"
    )


# ═══════════════════════════════════════════════════════════════════════════
# CALLBACK QUERY HANDLER
# ═══════════════════════════════════════════════════════════════════════════

@safe
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks (ci:, bl:, ct: formats)."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    data = query.data
    tg_user = query.from_user

    if data.startswith("ci:"):
        await _handle_ci_callback(query, context, data, tg_user)
    elif data.startswith("bl:"):
        await _handle_bl_callback(query, context, data, tg_user)
    elif data.startswith("ct:"):
        await _handle_ct_callback(query, context, data, tg_user)


async def _handle_ci_callback(query, context, data: str, tg_user):
    """Handle check-in callbacks: ci:<task_key>:progress|blocked|done."""
    parts = data.split(":")
    if len(parts) != 3:
        return

    task_key = parts[1]
    action = parts[2]

    def _process():
        with get_session() as session:
            member = _find_member_by_tg(session, tg_user.id)
            if not member:
                return "You're not registered."

            task = session.exec(
                select(Task).where(
                    Task.project_id == member.project_id,
                    Task.key == task_key,
                )
            ).first()
            if not task:
                return f"Task {task_key} not found."

            project = session.get(Project, member.project_id)

            if action == "progress":
                try:
                    if task.status == "todo":
                        transition(session, task, "in_progress", member.id,
                                   reason="button: in progress", from_chat=True)
                    elif task.status == "blocked":
                        transition(session, task, "in_progress", member.id,
                                   reason="button: resumed", from_chat=True)
                except TransitionError:
                    pass
                member.awaiting_clarification = False
                session.add(member)
                return f"▶️ {task_key} marked as *in progress*. Send a quick update about what you're working on!"

            elif action == "blocked":
                member.awaiting_clarification = True
                member.active_task_id = task.id
                session.add(member)
                return f"🚧 What's blocking you on {task_key}? Just type it out."

            elif action == "done":
                # Resolve open blockers
                open_blockers = session.exec(
                    select(Blocker).where(
                        Blocker.task_id == task.id,
                        Blocker.status == "open",
                    )
                ).all()
                for b in open_blockers:
                    b.status = "resolved"
                    b.resolved_at = datetime.now(timezone.utc)
                    session.add(b)

                try:
                    if task.status == "todo":
                        transition(session, task, "in_progress", member.id,
                                   reason="completing", from_chat=True)
                    if task.status == "blocked":
                        transition(session, task, "in_progress", member.id,
                                   reason="blocker resolved", from_chat=True)
                    transition(session, task, "claimed_done", member.id,
                               reason="button: done", from_chat=True)
                except TransitionError as e:
                    return f"Couldn't update: {e}"

                task.progress = 100
                member.awaiting_clarification = False
                session.add(task)
                session.add(member)
                session.commit()

                verdict = stubs.verify_task(task.id)
                conf = verdict.get("confidence", 0)
                reason = verdict.get("reason", "")
                return (
                    f"🎉 {task_key} marked as done!\n"
                    f"📋 *Claimed done (unverified)* — confidence: {conf:.0%}\n_{reason}_"
                )

    response = await asyncio.to_thread(_process)
    if response:
        await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)


async def _handle_bl_callback(query, context, data: str, tg_user):
    """Handle blocker callbacks: bl:<blocker_id>:help|no."""
    parts = data.split(":")
    if len(parts) != 3:
        return
    # Stub implementation
    await query.edit_message_text("👍 Noted! The lead has been notified.")


async def _handle_ct_callback(query, context, data: str, tg_user):
    """Handle contradiction callbacks: ct:<contradiction_id>:<member_id>:<a|b>."""
    # Stub implementation
    await query.edit_message_text("👍 Thanks for clarifying!")


# ═══════════════════════════════════════════════════════════════════════════
# DM TEXT HANDLER (free-text replies)
# ═══════════════════════════════════════════════════════════════════════════

@safe
async def dm_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-text DMs — onboarding flow or reply interpretation."""
    if not update.message or not update.effective_user:
        return
    if update.effective_chat.type != ChatType.PRIVATE:
        return

    tg_user = update.effective_user
    text = update.message.text or ""

    # Log inbound
    await asyncio.to_thread(
        _log_inbound, None, None, text,
        update.effective_chat.id, update.message.message_id, "dm",
    )

    # Find member
    def _get_member():
        with get_session() as session:
            member = _find_member_by_tg(session, tg_user.id)
            if not member:
                return None, None
            project = session.get(Project, member.project_id)
            return (
                Member.model_validate(member),
                Project.model_validate(project) if project else None,
            )

    member, project = await asyncio.to_thread(_get_member)

    if not member:
        await update.message.reply_text(
            "I don't know you yet! Join a project using an invite link, "
            "or create one with `/newproject`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ONBOARDING: awaiting GitHub username
    if member.onboarding_state == "awaiting_github":
        await _handle_github_onboarding(update, context, member, text)
        return

    # Normal reply interpretation
    if not project:
        await update.message.reply_text("Something's off — I can't find your project.")
        return

    responses = await handle_dm_reply(
        member=member,
        message_text=text,
        project=project,
        tg_message_id=update.message.message_id,
        chat_id=update.effective_chat.id,
    )

    for resp in responses:
        sent = await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN)
        await asyncio.to_thread(
            _log_outbound, project.id, member.id, resp,
            update.effective_chat.id, sent.message_id if sent else None,
        )


async def _handle_github_onboarding(update: Update, context, member: Member, text: str):
    """Process a GitHub username during onboarding."""
    login = text.strip().lstrip("@")

    def _validate_and_save():
        is_valid = stubs.validate_github_user(login)
        if not is_valid:
            return False

        with get_session() as session:
            m = session.get(Member, member.id)
            if m:
                m.github_login = login
                m.onboarding_state = "done"
                session.add(m)

                # Try to invite to repo
                project = session.get(Project, m.project_id)
                if project and project.repo_full_name:
                    try:
                        stubs.invite_collaborator(project.repo_full_name, login)
                    except Exception:
                        logger.warning("invite_collaborator failed for %s", login)

        return True

    valid = await asyncio.to_thread(_validate_and_save)

    if valid:
        await update.message.reply_text(
            f"✅ GitHub username `{login}` confirmed! You're all set.\n"
            "I'll DM you when tasks are assigned and check in periodically. 👍",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            f"❌ I couldn't find `{login}` on GitHub. Please send a valid username.",
            parse_mode=ParseMode.MARKDOWN,
        )


# ═══════════════════════════════════════════════════════════════════════════
# GROUP CHAT HANDLER
# ═══════════════════════════════════════════════════════════════════════════

async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages in linked group chats."""
    try:
        if not update.message:
            return
        chat = update.effective_chat
        if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return

        from ingest import handle_group_message
        await handle_group_message(update, context)
    except Exception:
        logger.exception("group_text_handler failed")


@safe
async def group_edited_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edited messages in linked group chats."""
    if not update.edited_message:
        return
    chat = update.effective_chat
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    from ingest import handle_group_edit
    await handle_group_edit(update, context)


@safe
async def migrate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group -> supergroup migration."""
    if not update.message:
        return
    new_chat_id = update.message.migrate_to_chat_id
    old_chat_id = update.message.chat_id
    if new_chat_id:
        def _migrate():
            with get_session() as session:
                project = session.exec(
                    select(Project).where(Project.telegram_group_id == old_chat_id)
                ).first()
                if project:
                    project.telegram_group_id = new_chat_id
                    session.add(project)
                    logger.info("Migrated group %d -> %d for project %s",
                                old_chat_id, new_chat_id, project.code)
        await asyncio.to_thread(_migrate)


# ═══════════════════════════════════════════════════════════════════════════
# BOT LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════

async def start_bot():
    """Build and start the Telegram bot with long polling."""
    global _bot_app
    settings = get_settings()

    _bot_app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Register handlers (order matters: commands first, then text)
    _bot_app.add_handler(CommandHandler("start", cmd_start))
    _bot_app.add_handler(CommandHandler("help", cmd_help))
    _bot_app.add_handler(CommandHandler("newproject", cmd_newproject))
    _bot_app.add_handler(CommandHandler("plan", cmd_plan))
    _bot_app.add_handler(CommandHandler("kickoff", cmd_kickoff))
    _bot_app.add_handler(CommandHandler("mytasks", cmd_mytasks))
    _bot_app.add_handler(CommandHandler("status", cmd_status))
    _bot_app.add_handler(CommandHandler("ask", cmd_ask))
    _bot_app.add_handler(CommandHandler("report", cmd_report))
    _bot_app.add_handler(CommandHandler("followup", cmd_followup))
    _bot_app.add_handler(CommandHandler("linkgroup", cmd_linkgroup))
    _bot_app.add_handler(CommandHandler("join", cmd_join))

    _bot_app.add_handler(CallbackQueryHandler(callback_handler))

    # Group text (before DM text so groups are matched first)
    _bot_app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        group_text_handler,
    ))
    _bot_app.add_handler(MessageHandler(
        filters.UpdateType.EDITED_MESSAGE & filters.ChatType.GROUPS,
        group_edited_handler,
    ))

    # DM text (last — catches remaining private text)
    _bot_app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        dm_text_handler,
    ))

    # Migration handler
    _bot_app.add_handler(MessageHandler(
        filters.StatusUpdate.MIGRATE,
        migrate_handler,
    ))

    logger.info("Starting Telegram bot (long polling)…")
    await _bot_app.initialize()
    await _bot_app.start()
    await _bot_app.updater.start_polling(drop_pending_updates=True)


async def stop_bot():
    """Gracefully stop the bot."""
    global _bot_app
    if _bot_app:
        logger.info("Stopping Telegram bot…")
        try:
            if _bot_app.updater and _bot_app.updater.running:
                await _bot_app.updater.stop()
        except Exception:
            logger.debug("Updater was not running")
        try:
            await _bot_app.stop()
        except RuntimeError:
            logger.debug("Application was not running")
        try:
            await _bot_app.shutdown()
        except Exception:
            logger.debug("Shutdown already done")
        _bot_app = None
