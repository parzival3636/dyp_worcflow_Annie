"""
Pilot – core loop: state machine, check-in scheduling, reply handling.

transition()       – single function for all status changes
checkin_tick()     – periodic check-in selector and sender
handle_dm_reply()  – interpret free-text DM and apply results
apply_observations() – apply P3G group observations
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select, col

from config import get_settings
from db import get_session
from models import (
    Blocker, Event, Member, Message, Project, Task,
)
from prompts import (
    P3Reply, P3Result, P3_SYSTEM, p3_user_prompt,
    CheckinMessage, CHECKIN_SYSTEM, checkin_user_prompt,
    GroupExtraction, Observation,
)
from llm import call_json
import stubs

logger = logging.getLogger("pilot.loop")

_scheduler: AsyncIOScheduler | None = None

# ═══════════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "todo":           {"in_progress"},
    "in_progress":    {"blocked", "claimed_done"},
    "blocked":        {"in_progress", "claimed_done"},
    "claimed_done":   {"verified_done", "needs_review"},
    "needs_review":   {"claimed_done", "verified_done"},
    "verified_done":  {"in_progress"},  # lead reopens
}

# Transitions that chat (DM or group) can NEVER produce
CHAT_FORBIDDEN_TARGETS = {"verified_done", "needs_review"}


class TransitionError(Exception):
    """Raised when a status transition is not allowed."""
    pass


def transition(
    session: Session,
    task: Task,
    new_status: str,
    actor_member_id: int | None,
    reason: str = "",
    *,
    from_chat: bool = False,
) -> None:
    """
    Validate, apply and log a task status change in the current transaction.

    Args:
        session: Active SQLModel session (caller manages commit).
        task: The task to update.
        new_status: Target status.
        actor_member_id: Who caused the change.
        reason: Human-readable reason for the event payload.
        from_chat: True if the trigger is a DM or group message.
                   Forbids verified_done and needs_review.

    Raises:
        TransitionError if the transition is not allowed.
    """
    old_status = task.status

    # Chat messages can never produce verified_done or needs_review
    if from_chat and new_status in CHAT_FORBIDDEN_TARGETS:
        raise TransitionError(
            f"Chat cannot transition to {new_status} (only verifier/lead can)"
        )

    # Check allowed graph
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise TransitionError(
            f"Transition {old_status} -> {new_status} is not allowed"
        )

    # Apply
    task.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "in_progress" and not task.started_at:
        task.started_at = now
    if new_status in ("claimed_done", "verified_done"):
        task.completed_at = now

    session.add(task)

    # Write event in the same transaction
    event = Event(
        project_id=task.project_id,
        ts=now,
        actor_member_id=actor_member_id,
        type="status_changed",
        task_id=task.id,
        payload={
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        },
    )
    session.add(event)


# ═══════════════════════════════════════════════════════════════════════════
# CHECK-IN TICK
# ═══════════════════════════════════════════════════════════════════════════

async def checkin_tick():
    """
    Periodic job: find tasks due for a check-in, send DM to the owner.
    Bundles multiple tasks per member into one message.
    """
    try:
        settings = get_settings()
        now = datetime.now(timezone.utc)

        # In demo mode, skip quiet hours; otherwise respect them
        if not settings.demo_mode:
            # Quiet hours check (UTC-based, simple approach)
            if settings.quiet_hours_start <= now.hour or now.hour < settings.quiet_hours_end:
                if settings.quiet_hours_start > settings.quiet_hours_end:
                    # Wraps midnight: e.g. 22-08
                    if now.hour >= settings.quiet_hours_start or now.hour < settings.quiet_hours_end:
                        return
                else:
                    if settings.quiet_hours_start <= now.hour < settings.quiet_hours_end:
                        return

        cadence = timedelta(hours=settings.checkin_hours)
        if settings.demo_mode:
            cadence = timedelta(minutes=2)

        cooldown = timedelta(minutes=30)
        if settings.demo_mode:
            cooldown = timedelta(seconds=30)

        # Collect tasks per member
        member_tasks: dict[int, list[Task]] = {}

        def _collect():
            with get_session() as session:
                # Running projects only
                projects = session.exec(
                    select(Project).where(Project.status == "running")
                ).all()

                for project in projects:
                    tasks = session.exec(
                        select(Task).where(
                            Task.project_id == project.id,
                            col(Task.status).in_(["todo", "in_progress", "blocked"]),
                            Task.owner_member_id != None,  # noqa: E711
                        )
                    ).all()

                    for task in tasks:
                        due = False

                        # Cadence check
                        if task.last_checkin_at is None:
                            due = True
                        elif now - task.last_checkin_at >= cadence:
                            due = True

                        # Deadline proximity pings
                        if task.deadline:
                            time_left = task.deadline - now
                            if time_left <= timedelta(hours=0):
                                due = True  # overdue
                            elif time_left <= timedelta(hours=2):
                                due = True
                            elif time_left <= timedelta(hours=24):
                                due = True

                        if due and task.owner_member_id:
                            member_tasks.setdefault(task.owner_member_id, []).append(
                                Task.model_validate(task)
                            )

                # Return member info for cooldown checks
                member_info = {}
                for mid in member_tasks:
                    member = session.get(Member, mid)
                    if member:
                        member_info[mid] = {
                            "name": member.name or "there",
                            "telegram_id": member.telegram_id,
                            "active_task_id": member.active_task_id,
                        }

                        # Check cooldown: last outbound message to this member
                        last_out = session.exec(
                            select(Message)
                            .where(
                                Message.member_id == mid,
                                Message.direction == "out",
                                Message.source == "dm",
                            )
                            .order_by(col(Message.created_at).desc())
                        ).first()
                        if last_out and last_out.created_at:
                            if now - last_out.created_at < cooldown:
                                member_info[mid]["on_cooldown"] = True

                return member_info

        member_info = await asyncio.to_thread(_collect)

        # Send check-ins
        for member_id, tasks_list in member_tasks.items():
            info = member_info.get(member_id)
            if not info or not info.get("telegram_id"):
                continue
            if info.get("on_cooldown") and not settings.demo_mode:
                continue

            # Bundle tasks into one message
            await _send_checkin(member_id, info, tasks_list)

    except Exception:
        logger.exception("checkin_tick failed")


async def _send_checkin(member_id: int, info: dict, tasks: list[Task]):
    """Generate and send a check-in message for one member."""
    from bot import _bot_app
    if not _bot_app:
        return

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        # Pick the most urgent task as the focus
        # Priority: overdue > closest deadline > lowest progress > first
        focus_task = tasks[0]
        for t in tasks:
            if t.deadline:
                if focus_task.deadline is None or t.deadline < focus_task.deadline:
                    focus_task = t

        # Generate check-in text via LLM
        deadline_str = focus_task.deadline.strftime("%b %d, %H:%M UTC") if focus_task.deadline else None
        criteria = focus_task.acceptance_criteria if isinstance(focus_task.acceptance_criteria, list) else []

        checkin_msg = await call_json(
            CHECKIN_SYSTEM,
            checkin_user_prompt(
                member_name=info["name"],
                task_key=focus_task.key,
                task_title=focus_task.title or "",
                task_status=focus_task.status,
                deadline=deadline_str,
                acceptance_criteria=[str(c) for c in criteria],
                checkin_count=focus_task.checkin_count,
            ),
            CheckinMessage,
        )

        text = checkin_msg.text
        if not text:
            text = f"Hey {info['name']}! How's {focus_task.key} (\"{focus_task.title}\") going?"

        # If multiple tasks, append a brief list
        if len(tasks) > 1:
            other_keys = [t.key for t in tasks if t.key != focus_task.key][:3]
            text += f"\n\n📋 Also on your plate: {', '.join(other_keys)}"

        # Buttons
        buttons = [
            [
                InlineKeyboardButton("▶️ In progress", callback_data=f"ci:{focus_task.key}:progress"),
                InlineKeyboardButton("🚧 Blocked", callback_data=f"ci:{focus_task.key}:blocked"),
                InlineKeyboardButton("✅ Done", callback_data=f"ci:{focus_task.key}:done"),
            ]
        ]

        sent = await _bot_app.bot.send_message(
            chat_id=info["telegram_id"],
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        # Update DB
        def _update_db():
            with get_session() as session:
                # Update task
                task = session.get(Task, focus_task.id)
                if task:
                    task.last_checkin_at = datetime.now(timezone.utc)
                    task.checkin_count = (task.checkin_count or 0) + 1
                    session.add(task)

                # Set active_task_id on member
                member = session.get(Member, member_id)
                if member:
                    member.active_task_id = focus_task.id
                    session.add(member)

                # Log outbound message
                msg = Message(
                    project_id=focus_task.project_id,
                    member_id=member_id,
                    task_id=focus_task.id,
                    direction="out",
                    text=text,
                    source="dm",
                    chat_id=info["telegram_id"],
                    tg_message_id=sent.message_id if sent else None,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(msg)

                # Event
                event = Event(
                    project_id=focus_task.project_id,
                    ts=datetime.now(timezone.utc),
                    type="checkin_sent",
                    task_id=focus_task.id,
                    actor_member_id=member_id,
                    payload={"checkin_count": task.checkin_count if task else 0},
                )
                session.add(event)

                # Escalation check
                if task and task.checkin_count and task.checkin_count >= 3:
                    stubs.escalate_to_lead(member_id, focus_task.id)

        await asyncio.to_thread(_update_db)

    except Exception:
        logger.exception("Failed to send check-in to member %d", member_id)


# ═══════════════════════════════════════════════════════════════════════════
# DM REPLY HANDLING
# ═══════════════════════════════════════════════════════════════════════════

async def handle_dm_reply(
    member: Member,
    message_text: str,
    project: Project,
    tg_message_id: int | None = None,
    chat_id: int | None = None,
) -> list[str]:
    """
    Interpret a free-text DM reply and apply status changes.

    Returns a list of response strings to send back to the member.
    """
    responses: list[str] = []

    try:
        # Gather member's open tasks
        def _get_tasks():
            with get_session() as session:
                tasks = session.exec(
                    select(Task).where(
                        Task.project_id == project.id,
                        Task.owner_member_id == member.id,
                        col(Task.status).in_(["todo", "in_progress", "blocked", "claimed_done"]),
                    )
                ).all()
                task_data = []
                for t in tasks:
                    # Get open blockers for this task
                    blockers = session.exec(
                        select(Blocker).where(
                            Blocker.task_id == t.id,
                            Blocker.status == "open",
                        )
                    ).all()
                    task_data.append({
                        "key": t.key,
                        "title": t.title,
                        "status": t.status,
                        "id": t.id,
                        "blockers": [b.description or "" for b in blockers],
                    })
                active_key = None
                if member.active_task_id:
                    active_task = session.get(Task, member.active_task_id)
                    if active_task:
                        active_key = active_task.key
                return task_data, active_key

        task_data, active_key = await asyncio.to_thread(_get_tasks)

        if not task_data:
            return ["You don't have any open tasks right now! 🎉"]

        # Call P3
        p3_result = await call_json(
            P3_SYSTEM,
            p3_user_prompt(
                member_name=member.name or "there",
                tasks=task_data,
                message_text=message_text,
                active_task_key=active_key,
            ),
            P3Reply,
        )

        # Process each result
        for result in p3_result.results:
            resp = await _apply_p3_result(result, member, project, task_data, message_text)
            if resp:
                responses.append(resp)

        # If no results produced, the LLM returned empty
        if not p3_result.results:
            responses.append("I couldn't quite parse that. Could you tell me which task you're talking about and what's the update?")

        # Log the inbound message with parsed JSON
        def _log_msg():
            with get_session() as session:
                msg = Message(
                    project_id=project.id,
                    member_id=member.id,
                    direction="in",
                    text=message_text,
                    parsed_json=p3_result.model_dump(),
                    source="dm",
                    chat_id=chat_id,
                    tg_message_id=tg_message_id,
                    created_at=datetime.now(timezone.utc),
                    processed=True,
                )
                session.add(msg)

                event = Event(
                    project_id=project.id,
                    ts=datetime.now(timezone.utc),
                    actor_member_id=member.id,
                    type="reply_received",
                    payload={"text_preview": message_text[:200]},
                )
                session.add(event)

        await asyncio.to_thread(_log_msg)

    except Exception:
        logger.exception("handle_dm_reply failed")
        responses.append("Something went wrong processing your update. Try again in a moment.")

    return responses if responses else ["Got it, thanks! 👍"]


async def _apply_p3_result(
    result: P3Result,
    member: Member,
    project: Project,
    task_data: list[dict],
    original_text: str,
) -> str | None:
    """Apply a single P3 result and return a response string."""

    # Low confidence → clarify
    if result.confidence < 0.6:
        q = result.clarification_question or "Could you clarify what you mean? Which task is this about?"
        return f"🤔 {q}"

    # Off-topic / unclear
    if result.intent in ("off_topic", "unclear"):
        if result.needs_clarification and result.clarification_question:
            return f"🤔 {result.clarification_question}"
        if result.intent == "off_topic":
            return None  # Silently ignore
        return "Could you clarify which task you're updating and what's the status?"

    # Find the task
    task_key = result.task_key
    if not task_key and len(task_data) == 1:
        task_key = task_data[0]["key"]

    if not task_key:
        return "Which task is this about? " + ", ".join(t["key"] for t in task_data)

    # Look up task in DB and apply
    def _apply():
        with get_session() as session:
            task = session.exec(
                select(Task).where(
                    Task.project_id == project.id,
                    Task.key == task_key,
                )
            ).first()
            if not task:
                return f"I couldn't find task {task_key}."

            # Verify ownership
            if task.owner_member_id != member.id:
                return f"Task {task_key} isn't assigned to you — I've noted your input though."

            response = ""

            if result.intent == "progress_update":
                try:
                    if task.status == "todo":
                        transition(session, task, "in_progress", member.id,
                                   reason=result.evidence_quote, from_chat=True)
                    elif task.status == "blocked":
                        # If they're reporting progress, maybe the blocker is resolved
                        transition(session, task, "in_progress", member.id,
                                   reason=result.evidence_quote, from_chat=True)
                except TransitionError:
                    pass  # Already in_progress is fine

                if result.progress is not None:
                    task.progress = result.progress
                    session.add(task)

                response = f"📝 Got it! {task_key} is in progress."
                if result.progress:
                    response += f" ({result.progress}% done)"

                # Clear clarification state
                m = session.get(Member, member.id)
                if m:
                    m.awaiting_clarification = False
                    session.add(m)

            elif result.intent == "blocker":
                # Blocker outranks completion
                blocker_info = result.blocker
                try:
                    if task.status in ("todo", "in_progress"):
                        transition(session, task, "blocked", member.id,
                                   reason=blocker_info.description if blocker_info else "blocked",
                                   from_chat=True)
                    elif task.status != "blocked":
                        transition(session, task, "blocked", member.id,
                                   reason=blocker_info.description if blocker_info else "blocked",
                                   from_chat=True)
                except TransitionError:
                    pass  # Already blocked is fine

                # Create blocker row
                b = Blocker(
                    task_id=task.id,
                    description=blocker_info.description if blocker_info else "Unknown blocker",
                    type=blocker_info.type if blocker_info else "other",
                    needed_from=blocker_info.needed_from if blocker_info else None,
                    status="open",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(b)
                session.flush()  # Get the ID

                # Event
                event = Event(
                    project_id=project.id,
                    ts=datetime.now(timezone.utc),
                    actor_member_id=member.id,
                    type="blocker_opened",
                    task_id=task.id,
                    payload={"blocker_id": b.id, "description": b.description},
                )
                session.add(event)

                response = f"🚧 {task_key} is now blocked: {b.description}"

                # Route blocker (after commit, via stub)
                session.commit()
                stubs.route_blocker(b.id)

                # Clear clarification
                m = session.get(Member, member.id)
                if m:
                    m.awaiting_clarification = False
                    session.add(m)

            elif result.intent == "completion_claim":
                # First resolve any open blockers
                open_blockers = session.exec(
                    select(Blocker).where(
                        Blocker.task_id == task.id,
                        Blocker.status == "open",
                    )
                ).all()
                for ob in open_blockers:
                    ob.status = "resolved"
                    ob.resolved_at = datetime.now(timezone.utc)
                    session.add(ob)

                    event = Event(
                        project_id=project.id,
                        ts=datetime.now(timezone.utc),
                        actor_member_id=member.id,
                        type="blocker_resolved",
                        task_id=task.id,
                        payload={"blocker_id": ob.id},
                    )
                    session.add(event)

                # Transition to claimed_done
                try:
                    if task.status in ("todo", "in_progress", "blocked"):
                        # Need to go through in_progress first if from todo
                        if task.status == "todo":
                            transition(session, task, "in_progress", member.id,
                                       reason="completing", from_chat=True)
                        if task.status == "blocked":
                            transition(session, task, "in_progress", member.id,
                                       reason="blocker resolved, completing", from_chat=True)
                        transition(session, task, "claimed_done", member.id,
                                   reason=result.evidence_quote, from_chat=True)
                    elif task.status == "needs_review":
                        transition(session, task, "claimed_done", member.id,
                                   reason=result.evidence_quote, from_chat=True)
                except TransitionError as e:
                    return f"Hmm, I couldn't update {task_key}: {e}"

                task.progress = 100
                session.add(task)

                # Clear clarification
                m = session.get(Member, member.id)
                if m:
                    m.awaiting_clarification = False
                    session.add(m)

                response = f"🎉 Nice! {task_key} marked as done!"

                # Commit so verify_task sees the data
                session.commit()

                # Call verification stub
                verdict = stubs.verify_task(task.id)
                confidence = verdict.get("confidence", 0)
                reason = verdict.get("reason", "")
                verdict_str = verdict.get("verdict", "no_evidence")

                if verdict_str == "no_evidence":
                    response += f"\n📋 *Claimed done (unverified)* — confidence: {confidence:.0%}\n_{reason}_"
                elif verdict_str == "needs_review":
                    response += f"\n🔍 *Needs review* — confidence: {confidence:.0%}\n_{reason}_"
                elif verdict_str == "verified_done":
                    response += f"\n✅ *Verified!* — confidence: {confidence:.0%}\n_{reason}_"

            elif result.intent == "question":
                answer = stubs.guide_answer(project.id, original_text)
                response = answer

            # Run post-hooks
            stubs.check_contradictions(project.id, task.id)
            stubs.recompute_ripple(project.id)

            return response

    resp = await asyncio.to_thread(_apply)
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# GROUP OBSERVATION APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

async def apply_observations(project: Project, extraction: GroupExtraction):
    """
    Apply P3G observations to the database using the same transition() function.
    """
    responses_for_group: list[str] = []

    for obs in extraction.observations:
        try:
            if obs.kind == "none" or obs.confidence < 0.6:
                continue

            resp = await _apply_single_observation(project, obs)
            if resp:
                responses_for_group.append(resp)

        except Exception:
            logger.exception("Failed to apply observation: %s", obs.kind)

    return responses_for_group


async def _apply_single_observation(project: Project, obs: Observation) -> str | None:
    """Apply one P3G observation."""

    def _apply():
        with get_session() as session:
            # Find the speaker member
            member = session.exec(
                select(Member).where(
                    Member.project_id == project.id,
                    Member.name == obs.speaker,
                )
            ).first()

            if not member:
                # Try by alias
                members = session.exec(
                    select(Member).where(Member.project_id == project.id)
                ).all()
                for m in members:
                    aliases = m.aliases if isinstance(m.aliases, list) else []
                    if obs.speaker.lower() in [a.lower() for a in aliases]:
                        member = m
                        break
                    if m.name and obs.speaker.lower() == m.name.split()[0].lower():
                        member = m
                        break

            if not member:
                logger.warning("Unknown speaker in group: %s", obs.speaker)
                return None

            # claim_about_other → no status change, pass to contradictions
            if obs.kind == "claim_about_other":
                task = None
                if obs.task_key:
                    task = session.exec(
                        select(Task).where(
                            Task.project_id == project.id,
                            Task.key == obs.task_key,
                        )
                    ).first()
                stubs.check_contradictions(project.id, task.id if task else None)
                return None

            # commitment → event only
            if obs.kind == "commitment":
                event = Event(
                    project_id=project.id,
                    ts=datetime.now(timezone.utc),
                    actor_member_id=member.id,
                    type="commitment_made",
                    payload={
                        "text": obs.commitment_text or obs.evidence_quote,
                        "task_key": obs.task_key,
                    },
                )
                session.add(event)
                return None

            # question → ignore unless bot was mentioned (handled elsewhere)
            if obs.kind == "question":
                return None

            # For progress / blocker / completion_claim, find the task
            if not obs.task_key:
                return None

            task = session.exec(
                select(Task).where(
                    Task.project_id == project.id,
                    Task.key == obs.task_key,
                )
            ).first()
            if not task:
                return None

            # Only the task owner's own messages change status
            is_owner = (task.owner_member_id == member.id)
            if not is_owner and task.owner_member_id:
                task_owner = session.get(Member, task.owner_member_id)
                if task_owner:
                    if (task_owner.telegram_id and member.telegram_id and task_owner.telegram_id == member.telegram_id) or \
                       (task_owner.telegram_username and member.telegram_username and task_owner.telegram_username.lower() == member.telegram_username.lower()) or \
                       (task_owner.name and member.name and (task_owner.name.lower() in member.name.lower() or member.name.lower() in task_owner.name.lower())):
                        is_owner = True
                        member = task_owner  # bind to the actual task owner

            if not is_owner:
                stubs.check_contradictions(project.id, task.id)
                return None

            if obs.kind == "progress":
                try:
                    if task.status == "todo":
                        transition(session, task, "in_progress", member.id,
                                   reason=obs.evidence_quote, from_chat=True)
                    elif task.status == "blocked":
                        transition(session, task, "in_progress", member.id,
                                   reason=obs.evidence_quote, from_chat=True)
                except TransitionError:
                    pass
                if obs.progress is not None:
                    task.progress = obs.progress
                    session.add(task)
                return None  # Silent in group

            elif obs.kind == "blocker":
                try:
                    if task.status in ("todo", "in_progress"):
                        if task.status == "todo":
                            transition(session, task, "in_progress", member.id,
                                       reason="starting", from_chat=True)
                        transition(session, task, "blocked", member.id,
                                   reason=obs.evidence_quote, from_chat=True)
                except TransitionError:
                    pass

                # Create blocker row
                blocker_desc = obs.blocker.description if obs.blocker else obs.evidence_quote
                b = Blocker(
                    task_id=task.id,
                    description=blocker_desc,
                    type=obs.blocker.type if obs.blocker else "other",
                    needed_from=obs.blocker.needed_from if obs.blocker else None,
                    status="open",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(b)
                session.flush()

                event = Event(
                    project_id=project.id,
                    ts=datetime.now(timezone.utc),
                    actor_member_id=member.id,
                    type="blocker_opened",
                    task_id=task.id,
                    payload={"blocker_id": b.id, "description": b.description},
                )
                session.add(event)
                session.commit()
                stubs.route_blocker(b.id)
                return None  # Silent, optionally react

            elif obs.kind == "completion_claim":
                # Resolve any open blockers first
                open_blockers = session.exec(
                    select(Blocker).where(
                        Blocker.task_id == task.id,
                        Blocker.status == "open",
                    )
                ).all()
                for ob in open_blockers:
                    ob.status = "resolved"
                    ob.resolved_at = datetime.now(timezone.utc)
                    session.add(ob)

                # Auto-resolve any false contradictions for this task
                try:
                    open_contradictions = session.exec(
                        select(Contradiction).where(
                            Contradiction.project_id == project.id,
                            Contradiction.status == "open",
                        )
                    ).all()
                    for oc in open_contradictions:
                        tids_str = [str(x) for x in (oc.task_ids or [])]
                        if str(task.id) in tids_str or task.key.lower() in (oc.summary or "").lower():
                            oc.status = "resolved"
                            oc.resolved_at = datetime.now(timezone.utc)
                            session.add(oc)
                except Exception:
                    pass

                try:
                    if task.status == "todo":
                        transition(session, task, "in_progress", member.id,
                                   reason="completing", from_chat=True)
                    if task.status == "blocked":
                        transition(session, task, "in_progress", member.id,
                                   reason="blocker resolved", from_chat=True)
                    transition(session, task, "claimed_done", member.id,
                               reason=obs.evidence_quote, from_chat=True)
                except TransitionError:
                    task.status = "claimed_done"
                    session.add(task)

                task.progress = 100
                session.add(task)
                session.commit()
                stubs.verify_task(task.id)
                return None  # Silent in group

            stubs.check_contradictions(project.id, task.id if task else None)
            stubs.recompute_ripple(project.id)
            return None

    return await asyncio.to_thread(_apply)


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def start_scheduler():
    """Start APScheduler with the check-in tick job."""
    global _scheduler
    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    interval = 60  # seconds
    if settings.demo_mode:
        interval = 20

    _scheduler.add_job(
        checkin_tick,
        "interval",
        seconds=interval,
        id="checkin_tick",
        max_instances=1,
    )

    try:
        from verify import run_github_poll_tick
        poll_sec = getattr(settings, "github_poll_seconds", 45) or 45
        _scheduler.add_job(
            run_github_poll_tick,
            "interval",
            seconds=poll_sec,
            id="github_poll",
            max_instances=1,
        )
        logger.info("GitHub commit polling job scheduled every %ds", poll_sec)
    except Exception as exc:
        logger.warning("Could not schedule GitHub poll job: %s", exc)

    _scheduler.start()
    logger.info("Scheduler started (interval=%ds, demo=%s)", interval, settings.demo_mode)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
