import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlmodel import Session, select, desc

from backend.config import settings
from backend.models import Project, Member, Task, TaskDep, Blocker, Event
from backend.events import add_event
from backend.state import transition_task
from backend.llm import call_json, P6Route
from backend.prompts import P6_ROUTING_PROMPT


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_already_asked_member_ids(session: Session, blocker_id: int) -> set[int]:
    """Finds all members who were previously routed this blocker."""
    events = session.exec(
        select(Event).where(
            Event.type == "blocker_routed",
        )
    ).all()
    asked = set()
    for e in events:
        if e.payload and e.payload.get("blocker_id") == blocker_id:
            mid = e.actor_member_id or e.payload.get("routed_to_member_id")
            if mid:
                asked.add(mid)
    return asked


def get_candidate_helpers(
    session: Session,
    blocker: Blocker,
    exclude_member_ids: Optional[set[int]] = None,
) -> list[Member]:
    """
    Ranks potential helper candidates:
    1. Owner of task/dependency referenced in needed_from or upstream tasks.
    2. Members whose skills match the blocker description.
    3. The project lead.
    4. Remaining team members.
    Excludes the blocked task owner and anyone already asked.
    """
    task = session.get(Task, blocker.task_id)
    if not task:
        return []

    project_id = task.project_id
    project = session.get(Project, project_id)
    all_members = session.exec(select(Member).where(Member.project_id == project_id)).all()

    exclude = set(exclude_member_ids or set())
    if task.owner_member_id:
        exclude.add(task.owner_member_id)

    candidates: list[Member] = []
    added_ids: set[int] = set()

    def add_candidate(m: Optional[Member]):
        if m and m.id not in exclude and m.id not in added_ids:
            candidates.append(m)
            added_ids.add(m.id)

    # 1. Check needed_from for a task key (e.g. "T-3") or member name
    needed_from = (blocker.needed_from or "").strip()
    if needed_from:
        # Check if needed_from is a task key
        dep_task = session.exec(
            select(Task).where(Task.project_id == project_id, Task.key == needed_from)
        ).first()
        if dep_task and dep_task.owner_member_id:
            add_candidate(session.get(Member, dep_task.owner_member_id))

        # Check if needed_from is a member name
        matching_member = session.exec(
            select(Member).where(Member.project_id == project_id, Member.name.ilike(f"%{needed_from}%"))
        ).first()
        if matching_member:
            add_candidate(matching_member)

    # Check upstream dependency task owners
    upstream_deps = session.exec(
        select(TaskDep).where(TaskDep.task_id == task.id)
    ).all()
    for d in upstream_deps:
        parent_task = session.get(Task, d.depends_on_task_id)
        if parent_task and parent_task.owner_member_id:
            add_candidate(session.get(Member, parent_task.owner_member_id))

    # 2. Skill match
    blocker_text = f"{blocker.description or ''} {blocker.type or ''}".lower()
    blocker_words = set(re.findall(r"\w+", blocker_text))

    skill_ranked = []
    for m in all_members:
        if m.id not in exclude and m.id not in added_ids:
            m_skills = set(re.findall(r"\w+", (m.skills or "").lower()))
            overlap = len(blocker_words.intersection(m_skills))
            skill_ranked.append((overlap, m))

    skill_ranked.sort(key=lambda item: item[0], reverse=True)
    for overlap, m in skill_ranked:
        if overlap > 0:
            add_candidate(m)

    # 3. Project lead
    lead = next((m for m in all_members if m.role == "lead"), None)
    if not lead and project and project.lead_member_id:
        lead = session.get(Member, project.lead_member_id)
    add_candidate(lead)

    # 4. Remaining members
    for m in all_members:
        add_candidate(m)

    return candidates


def route_blocker(
    session: Session,
    blocker_id: int,
    extra_exclude: Optional[set[int]] = None,
) -> dict[str, Any]:
    """
    Selects the best helper candidate, calls LLM (P6) with candidates, updates blocker,
    records blocker_routed event, and returns the outbound message object for Person A.
    """
    blocker = session.get(Blocker, blocker_id)
    if not blocker:
        raise ValueError(f"Blocker {blocker_id} not found")

    task = session.get(Task, blocker.task_id)
    if not task:
        raise ValueError(f"Task for blocker {blocker_id} not found")

    blocked_member = session.get(Member, task.owner_member_id) if task.owner_member_id else None
    blocked_name = blocked_member.name if blocked_member else "A team member"

    already_asked = get_already_asked_member_ids(session, blocker_id)
    if extra_exclude:
        already_asked.update(extra_exclude)
    candidates = get_candidate_helpers(session, blocker, exclude_member_ids=already_asked)

    if not candidates:
        # Fallback to lead if everyone was asked
        all_members = session.exec(select(Member).where(Member.project_id == task.project_id)).all()
        lead = next((m for m in all_members if m.role == "lead"), all_members[0])
        chosen_candidate = lead
        reason = "All candidates asked; escalating to lead"
    else:
        # Prompt P6 with candidates
        candidates_str = "\n".join(
            f"- Member ID {m.id}: {m.name} (Role: {m.role}, Skills: {m.skills or 'None'})"
            for m in candidates
        )
        user_prompt = (
            f"Blocker: {blocker.description}\n"
            f"Type: {blocker.type or 'unspecified'}\n"
            f"Needed From: {blocker.needed_from or 'unspecified'}\n"
            f"Task: {task.key} ({task.title})\n\n"
            f"Eligible Candidates:\n{candidates_str}\n\n"
            f"Select the best candidate member_id."
        )

        p6_result: P6Route = call_json(P6_ROUTING_PROMPT, user_prompt, P6Route)
        candidate_ids = {m.id for m in candidates}

        if p6_result.member_id in candidate_ids:
            chosen_candidate = next(m for m in candidates if m.id == p6_result.member_id)
            reason = p6_result.reason
        else:
            # Fallback to first priority candidate if LLM gave an invalid ID
            chosen_candidate = candidates[0]
            reason = f"Rank-1 candidate chosen ({candidates[0].name})"

    # Update blocker state
    blocker.status = "routed"
    blocker.routed_to_member_id = chosen_candidate.id
    session.add(blocker)

    # Write blocker_routed event
    add_event(
        session=session,
        project_id=task.project_id,
        type="blocker_routed",
        task_id=task.id,
        actor_member_id=chosen_candidate.id,
        payload={
            "blocker_id": blocker.id,
            "routed_to_member_id": chosen_candidate.id,
            "routed_to_name": chosen_candidate.name,
            "reason": reason,
        },
    )
    session.flush()

    message_text = f"{blocked_name} is blocked on {blocker.description or 'a dependency'} for {task.key}. Can you help?"
    return {
        "blocker_id": blocker.id,
        "member_id": chosen_candidate.id,
        "text": message_text,
        "buttons": [
            {"label": "I can help", "callback": f"blocker_accept:{blocker.id}"},
            {"label": "Not me", "callback": f"blocker_decline:{blocker.id}"},
        ],
    }


def on_helper_response(
    session: Session,
    blocker_id: int,
    member_id: int,
    accepted: bool,
) -> dict[str, Any]:
    """
    Called when a teammate clicks 'I can help' or 'Not me'.
    If accepted: locks routing to this helper.
    If declined: routes to the next candidate (or escalates to lead if all decline).
    """
    blocker = session.get(Blocker, blocker_id)
    if not blocker:
        raise ValueError(f"Blocker {blocker_id} not found")

    task = session.get(Task, blocker.task_id)

    if accepted:
        blocker.routed_to_member_id = member_id
        session.add(blocker)
        session.flush()
        return {
            "status": "accepted",
            "blocker_id": blocker.id,
            "helper_member_id": member_id,
            "text": f"Thank you! You are now assigned to help with blocker on {task.key}.",
        }
    else:
        # Route to next candidate, excluding the member who declined
        next_routing = route_blocker(session, blocker_id, extra_exclude={member_id})
        return {
            "status": "declined",
            "blocker_id": blocker.id,
            "next_outbound": next_routing,
        }


def check_blocker_timeouts(session: Session, project_id: int) -> list[dict[str, Any]]:
    """
    Escalates open/routed blockers that have had no response within timeout window:
    - Normal mode: 2 hours
    - DEMO_MODE: 2 minutes
    """
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    task_ids = {t.id: t for t in tasks}

    blockers = session.exec(
        select(Blocker).where(Blocker.task_id.in_(task_ids.keys()), Blocker.status == "routed")
    ).all()

    timeout_duration = timedelta(minutes=2) if settings.DEMO_MODE else timedelta(hours=2)
    now = datetime.now(timezone.utc)
    escalations = []

    for b in blockers:
        # Check last routed event for this blocker
        last_routed_event = session.exec(
            select(Event).where(
                Event.type == "blocker_routed",
                Event.task_id == b.task_id,
            ).order_by(desc(Event.ts))
        ).first()

        raw_time = last_routed_event.ts if last_routed_event and last_routed_event.ts else b.created_at
        routed_time = ensure_utc(raw_time)
        if routed_time and (now - routed_time) >= timeout_duration:
            # Timeout hit! Hop to next candidate
            outbound = route_blocker(session, b.id)
            escalations.append(outbound)

    session.flush()
    return escalations


def resolve_blocker(
    session: Session,
    blocker_id: int,
    by_member_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Resolves the blocker, transitions the task back to in_progress,
    and writes blocker_resolved event. Idempotent.
    """
    blocker = session.get(Blocker, blocker_id)
    if not blocker:
        raise ValueError(f"Blocker {blocker_id} not found")

    # Idempotent: already resolved
    if blocker.status == "resolved":
        return {"status": "already_resolved", "blocker_id": blocker.id}

    task = session.get(Task, blocker.task_id)
    now = datetime.now(timezone.utc)

    blocker.status = "resolved"
    blocker.resolved_at = now
    session.add(blocker)

    # Write blocker_resolved event
    add_event(
        session=session,
        project_id=task.project_id,
        type="blocker_resolved",
        task_id=task.id,
        actor_member_id=by_member_id or blocker.routed_to_member_id,
        payload={"blocker_id": blocker.id, "resolved_by": by_member_id},
    )

    # Transition task back to in_progress
    transition_task(
        session=session,
        task_key=task.key,
        project_id=task.project_id,
        new_status="in_progress",
        actor_member_id=by_member_id,
        reason="Blocker resolved",
        source="blocker",
    )

    session.flush()

    blocked_owner = session.get(Member, task.owner_member_id) if task.owner_member_id else None
    return {
        "status": "resolved",
        "blocker_id": blocker.id,
        "task_key": task.key,
        "notify_member_id": blocked_owner.id if blocked_owner else None,
        "text": f"Your blocker on {task.key} has been resolved! Task is now in_progress.",
    }
