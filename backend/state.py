from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import Session, select

try:
    from models import Task
    from events import add_event
except ImportError:
    from backend.models import Task
    from backend.events import add_event


class IllegalTransition(Exception):
    pass


VALID_STATUSES = {
    "todo",
    "in_progress",
    "blocked",
    "claimed_done",
    "needs_review",
    "verified_done",
}


def transition_task(
    session: Session,
    task_key: str,
    project_id: int,
    new_status: str,
    actor_member_id: Optional[int],
    reason: str,
    source: str,
    extra: Optional[dict[str, Any]] = None,
) -> Task:
    """
    Locks the task row with with_for_update(), validates the transition,
    updates the task, sets started_at/completed_at where relevant,
    writes a status_changed event, all within the caller's transaction.
    Raises IllegalTransition otherwise.
    """
    if new_status not in VALID_STATUSES:
        raise IllegalTransition(f"Unknown target status: {new_status}")

    # Lock the task row
    statement = (
        select(Task)
        .where(Task.project_id == project_id, Task.key == task_key)
        .with_for_update()
    )
    task = session.exec(statement).first()
    if not task:
        raise IllegalTransition(f"Task {task_key} not found in project {project_id}")

    current_status = task.status

    # Idempotent: Same-status transitions are no-ops (no event written)
    if current_status == new_status:
        return task

    # Chat reply can NEVER produce verified_done
    if new_status == "verified_done" and source not in {"verifier", "lead_override"}:
        raise IllegalTransition(
            f"Cannot transition to 'verified_done' from source '{source}'. Only 'verifier' or 'lead_override' allowed."
        )

    # Validate state machine transitions
    allowed = False

    if current_status == "todo":
        if new_status == "in_progress" and source in {"reply", "commit"}:
            allowed = True
        elif new_status == "claimed_done" and source in {"reply"}:
            allowed = True

    elif current_status == "in_progress":
        if new_status == "blocked" and source in {"blocker", "reply"}:
            allowed = True
        elif new_status == "claimed_done" and source in {"reply"}:
            allowed = True

    elif current_status == "blocked":
        if new_status == "in_progress" and source in {"blocker", "reply"}:
            allowed = True
        elif new_status == "claimed_done" and source in {"reply"}:
            allowed = True

    elif current_status == "claimed_done":
        if new_status == "verified_done":
            if source == "lead_override":
                allowed = True
            elif source == "verifier":
                verdict = (extra or {}).get("verdict", "verified")
                confidence = (extra or {}).get("confidence", 1.0)
                if verdict == "verified" and confidence >= 0.7:
                    allowed = True
                else:
                    raise IllegalTransition(
                        f"Verifier transition to verified_done requires verdict='verified' and confidence >= 0.7. Got verdict={verdict}, confidence={confidence}"
                    )
        elif new_status == "needs_review" and source in {"verifier", "lead_override"}:
            allowed = True

    elif current_status == "needs_review":
        if new_status == "claimed_done" and source in {"reply", "commit"}:
            allowed = True
        elif new_status == "verified_done" and source == "lead_override":
            allowed = True
        # Note: verifier cannot directly transition needs_review to verified_done (only lead_override)

    elif current_status == "verified_done":
        if new_status == "in_progress" and source == "lead_override":
            allowed = True

    if not allowed:
        raise IllegalTransition(
            f"Illegal transition from '{current_status}' to '{new_status}' with source='{source}'"
        )

    # State update side effects
    now = datetime.now(timezone.utc)

    # First move out of todo: set started_at
    if current_status == "todo" and task.started_at is None:
        task.started_at = now

    # Move to verified_done: set completed_at and progress=100
    if new_status == "verified_done":
        task.completed_at = now
        task.progress = 100
    elif extra and "progress" in extra and isinstance(extra["progress"], int):
        task.progress = extra["progress"]

    task.status = new_status
    session.add(task)

    # Write status_changed event in the same transaction
    add_event(
        session=session,
        project_id=project_id,
        type="status_changed",
        task_id=task.id,
        actor_member_id=actor_member_id,
        payload={
            "from_status": current_status,
            "to_status": new_status,
            "reason": reason,
            "source": source,
            "extra": extra or {},
        },
    )

    session.flush()
    return task
