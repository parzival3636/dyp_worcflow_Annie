from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import Session, select, desc

from backend.models import (
    Project,
    Member,
    Task,
    TaskDep,
    Message,
    Blocker,
    Contradiction,
    Verification,
    Event,
)
from backend.events import add_event
from backend.llm import call_json, P5Contradiction
from backend.prompts import P5_CONTRADICTION_PROMPT


def is_duplicate_contradiction(
    session: Session,
    project_id: int,
    task_ids: list[str],
    member_ids: list[int],
) -> bool:
    """Checks if an open contradiction already exists for the same tasks and members."""
    open_contradictions = session.exec(
        select(Contradiction).where(
            Contradiction.project_id == project_id,
            Contradiction.status == "open",
        )
    ).all()

    set_tasks = set(task_ids)
    set_members = set(member_ids)

    for c in open_contradictions:
        if set(c.task_ids or []) == set_tasks and set(c.member_ids or []) == set_members:
            return True
    return False


def create_contradiction(
    session: Session,
    project_id: int,
    task_ids: list[str],
    member_ids: list[int],
    summary: str,
    questions: Optional[list[str]] = None,
) -> Optional[Contradiction]:
    """
    Inserts a contradiction if not duplicate, writes contradiction_opened event,
    and returns the contradiction object.
    """
    if is_duplicate_contradiction(session, project_id, task_ids, member_ids):
        return None

    now = datetime.now(timezone.utc)
    contradiction = Contradiction(
        project_id=project_id,
        task_ids=task_ids,
        member_ids=member_ids,
        summary=summary,
        status="open",
        created_at=now,
    )
    session.add(contradiction)
    session.flush()

    add_event(
        session=session,
        project_id=project_id,
        type="contradiction_opened",
        payload={
            "contradiction_id": contradiction.id,
            "summary": summary,
            "task_ids": task_ids,
            "member_ids": member_ids,
            "questions": questions or [],
        },
    )
    session.flush()
    return contradiction


def check_contradictions(
    session: Session,
    project_id: int,
    trigger_task_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Runs rule-based and LLM-based contradiction detection.
    Returns list of outbound messages to send to conflicting members.
    """
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    task_map = {t.key: t for t in tasks}
    detected_outbound: list[dict[str, Any]] = []

    # Rule 3: claimed_done but latest verification is no_evidence
    verifications = session.exec(
        select(Verification).order_by(desc(Verification.created_at))
    ).all()
    latest_verification = {}
    for v in verifications:
        if v.task_id not in latest_verification:
            latest_verification[v.task_id] = v

    for t in tasks:
        if t.status == "claimed_done" and t.id in latest_verification:
            latest = latest_verification[t.id]
            if latest.verdict == "no_evidence":
                summary = f"Task {t.key} was claimed done, but verification found no matching evidence in git commits."
                member_id = t.owner_member_id or 1
                c = create_contradiction(
                    session=session,
                    project_id=project_id,
                    task_ids=[t.key],
                    member_ids=[member_id],
                    summary=summary,
                    questions=[f"You claimed {t.key} is done, but no git commits were found. Did you push your code?"],
                )
                if c:
                    detected_outbound.append({
                        "member_id": member_id,
                        "text": f"You claimed {t.key} is done, but verification found no evidence in git commits. Could you verify your branch/commits?",
                    })

    # Rule 1 & 2: Check recent member messages against task states
    recent_messages = session.exec(
        select(Message).where(Message.project_id == project_id, Message.direction == "in").order_by(desc(Message.created_at)).limit(20)
    ).all()

    # Rule 1: Member claims another task is done while it is not verified or its owner is blocked
    for msg in recent_messages:
        parsed = msg.parsed_json or {}
        claims = parsed.get("claims_about_others", [])
        for claim in claims:
            # Check if claim references another task (e.g. "T-7 is done" or "auth is done")
            for t_key, t in task_map.items():
                if t_key in claim or (t.title and t.title.lower() in claim.lower()):
                    if t.status == "blocked" or (t.status != "verified_done" and "done" in claim.lower()):
                        blocked_owner_id = t.owner_member_id or 1
                        claimant_id = msg.member_id or 1
                        if claimant_id != blocked_owner_id:
                            summary = f"Member claimed {t_key} is done, but task owner reported it is {t.status}."
                            q1 = f"You reported that {t_key} is completed, but its owner reported it is {t.status}. Which is accurate?"
                            q2 = f"Your teammate reported {t_key} is ready, but your task is marked {t.status}. Can you confirm status?"
                            c = create_contradiction(
                                session=session,
                                project_id=project_id,
                                task_ids=[t_key],
                                member_ids=[claimant_id, blocked_owner_id],
                                summary=summary,
                                questions=[q1, q2],
                            )
                            if c:
                                detected_outbound.append({"member_id": claimant_id, "text": q1})
                                detected_outbound.append({"member_id": blocked_owner_id, "text": q2})

    # LLM Check (P5)
    # Prepare message context for P5
    context_msgs = [f"Member {m.member_id}: {m.text}" for m in recent_messages[:6]]
    context_tasks = [f"Task {t.key} ({t.status})" for t in tasks[:8]]

    user_prompt = (
        f"Recent Messages:\n" + "\n".join(context_msgs) + "\n\n"
        f"Task Statuses:\n" + "\n".join(context_tasks) + "\n\n"
        f"Evaluate if there are conflicting claims."
    )

    p5_res: P5Contradiction = call_json(P5_CONTRADICTION_PROMPT, user_prompt, P5Contradiction)
    if p5_res.has_contradiction and p5_res.task_ids:
        c = create_contradiction(
            session=session,
            project_id=project_id,
            task_ids=p5_res.task_ids,
            member_ids=p5_res.member_ids,
            summary=p5_res.summary or "Conflicting status statements detected by AI Guide.",
            questions=p5_res.questions_to_ask,
        )
        if c:
            for idx, mid in enumerate(p5_res.member_ids):
                q = p5_res.questions_to_ask[idx] if idx < len(p5_res.questions_to_ask) else "Could you clarify the status of this task?"
                detected_outbound.append({"member_id": mid, "text": q})

    session.flush()
    return detected_outbound


def resolve_contradiction(
    session: Session,
    contradiction_id: int,
    resolution: str,
) -> dict[str, Any]:
    """Resolves an open contradiction, sets resolved_at and resolution, and emits event."""
    c = session.get(Contradiction, contradiction_id)
    if not c:
        raise ValueError(f"Contradiction {contradiction_id} not found")

    if c.status == "resolved":
        return {"status": "already_resolved", "id": c.id}

    c.status = "resolved"
    c.resolved_at = datetime.now(timezone.utc)
    c.resolution = resolution
    session.add(c)

    add_event(
        session=session,
        project_id=c.project_id or 1,
        type="contradiction_resolved",
        payload={
            "contradiction_id": c.id,
            "resolution": resolution,
            "task_ids": c.task_ids,
        },
    )
    session.flush()
    return {"status": "resolved", "id": c.id, "resolution": resolution}
