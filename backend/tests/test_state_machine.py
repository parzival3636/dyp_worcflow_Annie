"""
Pilot – test_state_machine.py

Tests every allowed/disallowed transition and event recording.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from models import Task, Event
from loop import transition, TransitionError, ALLOWED_TRANSITIONS, CHAT_FORBIDDEN_TARGETS


class FakeSession:
    """Minimal fake session for unit testing transition()."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


# ---------------------------------------------------------------------------
# Allowed transitions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("old,new", [
    ("todo", "in_progress"),
    ("in_progress", "blocked"),
    ("in_progress", "claimed_done"),
    ("blocked", "in_progress"),
    ("blocked", "claimed_done"),
    ("claimed_done", "verified_done"),
    ("claimed_done", "needs_review"),
    ("needs_review", "claimed_done"),
    ("needs_review", "verified_done"),
    ("verified_done", "in_progress"),
])
def test_allowed_transitions(old: str, new: str):
    """Every allowed transition should succeed and write an event."""
    task = Task(id=1, project_id=1, key="T-1", status=old)
    session = FakeSession()

    # verified_done and needs_review cannot come from chat
    from_chat = new not in CHAT_FORBIDDEN_TARGETS

    transition(session, task, new, actor_member_id=1, reason="test", from_chat=from_chat)

    assert task.status == new
    # Should have added: the task + an event
    events = [obj for obj in session.added if isinstance(obj, Event)]
    assert len(events) == 1
    assert events[0].type == "status_changed"
    assert events[0].payload["old_status"] == old
    assert events[0].payload["new_status"] == new


# ---------------------------------------------------------------------------
# Disallowed transitions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("old,new", [
    ("todo", "blocked"),
    ("todo", "claimed_done"),
    ("todo", "verified_done"),
    ("in_progress", "todo"),
    ("in_progress", "verified_done"),
    ("in_progress", "needs_review"),
    ("blocked", "todo"),
    ("blocked", "verified_done"),
    ("claimed_done", "in_progress"),
    ("claimed_done", "todo"),
    ("verified_done", "todo"),
    ("verified_done", "blocked"),
])
def test_disallowed_transitions(old: str, new: str):
    """Disallowed transitions should raise TransitionError."""
    task = Task(id=1, project_id=1, key="T-1", status=old)
    session = FakeSession()

    with pytest.raises(TransitionError):
        transition(session, task, new, actor_member_id=1, reason="test", from_chat=False)

    # Status should NOT have changed
    assert task.status == old


# ---------------------------------------------------------------------------
# Chat cannot produce verified_done or needs_review
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("forbidden", ["verified_done", "needs_review"])
def test_chat_cannot_produce_verified_or_needs_review(forbidden: str):
    """Chat messages can never produce verified_done or needs_review."""
    # Even if the graph allows it (e.g. claimed_done -> verified_done)
    task = Task(id=1, project_id=1, key="T-1", status="claimed_done")
    session = FakeSession()

    with pytest.raises(TransitionError, match="Chat cannot"):
        transition(session, task, forbidden, actor_member_id=1, reason="test", from_chat=True)

    assert task.status == "claimed_done"


# ---------------------------------------------------------------------------
# Event is always written on success
# ---------------------------------------------------------------------------

def test_event_written_on_every_success():
    """Every successful transition must write exactly one event."""
    for old, targets in ALLOWED_TRANSITIONS.items():
        for new in targets:
            task = Task(id=1, project_id=1, key="T-1", status=old)
            session = FakeSession()
            from_chat = new not in CHAT_FORBIDDEN_TARGETS
            transition(session, task, new, actor_member_id=1, from_chat=from_chat)
            events = [o for o in session.added if isinstance(o, Event)]
            assert len(events) == 1, f"Expected 1 event for {old}->{new}, got {len(events)}"


# ---------------------------------------------------------------------------
# Timestamps are set correctly
# ---------------------------------------------------------------------------

def test_started_at_set_on_in_progress():
    """started_at should be set when transitioning to in_progress."""
    task = Task(id=1, project_id=1, key="T-1", status="todo", started_at=None)
    session = FakeSession()
    transition(session, task, "in_progress", actor_member_id=1, from_chat=True)
    assert task.started_at is not None


def test_completed_at_set_on_claimed_done():
    """completed_at should be set when transitioning to claimed_done."""
    task = Task(id=1, project_id=1, key="T-1", status="in_progress", completed_at=None)
    session = FakeSession()
    transition(session, task, "claimed_done", actor_member_id=1, from_chat=True)
    assert task.completed_at is not None
