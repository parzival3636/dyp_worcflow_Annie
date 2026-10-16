from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import Session
from backend.models import Event

VALID_EVENT_TYPES = {
    "project_created",
    "member_joined",
    "task_created",
    "task_updated",
    "tasks_bundled",
    "block_assigned",
    "checkin_sent",
    "reply_received",
    "status_changed",
    "blocker_opened",
    "blocker_routed",
    "blocker_resolved",
    "contradiction_opened",
    "contradiction_resolved",
    "commit_seen",
    "verification_done",
    "risk_changed",
    "guide_note",
}


def add_event(
    session: Session,
    project_id: int,
    type: str,
    task_id: Optional[int] = None,
    actor_member_id: Optional[int] = None,
    payload: Optional[dict[str, Any]] = None,
) -> Event:
    """
    Appends an event within the caller's transaction.
    Does NOT commit; caller owns the transaction.
    """
    if type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event type: {type}. Must be one of {VALID_EVENT_TYPES}")

    event = Event(
        project_id=project_id,
        type=type,
        task_id=task_id,
        actor_member_id=actor_member_id,
        payload=payload or {},
        ts=datetime.now(timezone.utc),
    )
    session.add(event)
    session.flush()
    return event
