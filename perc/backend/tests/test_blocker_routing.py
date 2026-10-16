from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
import pytest

from backend.config import settings
from backend.models import Project, Member, Task, TaskDep, Blocker, Event
from backend.llm import P6Route
import backend.routing as routing_module
from backend.routing import (
    get_candidate_helpers,
    route_blocker,
    on_helper_response,
    check_blocker_timeouts,
    resolve_blocker,
)


def test_b1_needed_from_names_task_owner_is_first(session: Session, sample_project: Project):
    # Member 1 (Kabir, blocked), Member 2 (Meera, owns T-2)
    m_kabir = Member(project_id=sample_project.id, name="Kabir", role="member")
    m_meera = Member(project_id=sample_project.id, name="Meera", role="lead")
    session.add_all([m_kabir, m_meera])
    session.commit()

    t2 = Task(project_id=sample_project.id, key="T-2", title="Auth API", owner_member_id=m_meera.id)
    t7 = Task(project_id=sample_project.id, key="T-7", title="Payments", owner_member_id=m_kabir.id, status="blocked")
    session.add_all([t2, t7])
    session.commit()

    blocker = Blocker(task_id=t7.id, description="waiting on auth credentials", needed_from="T-2")
    session.add(blocker)
    session.commit()

    candidates = get_candidate_helpers(session, blocker)
    assert len(candidates) >= 1
    # Meera owns T-2, so Meera is rank-1 candidate
    assert candidates[0].id == m_meera.id


def test_b2_no_task_match_skill_match_next(session: Session, sample_project: Project):
    m_blocked = Member(project_id=sample_project.id, name="Alice", role="member")
    m_devops = Member(project_id=sample_project.id, name="Bob", role="member", skills="docker kubernetes aws")
    m_lead = Member(project_id=sample_project.id, name="Charlie", role="lead", skills="management")
    session.add_all([m_blocked, m_devops, m_lead])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-1", title="Setup Cluster", owner_member_id=m_blocked.id)
    session.add(t)
    session.commit()

    blocker = Blocker(task_id=t.id, description="Cannot connect to docker container", needed_from="")
    session.add(blocker)
    session.commit()

    candidates = get_candidate_helpers(session, blocker)
    # Bob has matching skill "docker", so precedes Charlie (lead)
    assert candidates[0].id == m_devops.id


def test_b3_p6_returns_invalid_id_uses_first_candidate(session: Session, sample_project: Project, monkeypatch):
    m1 = Member(project_id=sample_project.id, name="Kabir", role="member")
    m2 = Member(project_id=sample_project.id, name="Meera", role="lead")
    session.add_all([m1, m2])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-7", owner_member_id=m1.id, status="blocked")
    session.add(t)
    session.commit()

    blocker = Blocker(task_id=t.id, description="Need credentials")
    session.add(blocker)
    session.commit()

    # Mock P6 returning an unknown member ID 9999
    monkeypatch.setattr(
        routing_module,
        "call_json",
        lambda *args, **kwargs: P6Route(member_id=9999, reason="Hallucinated ID"),
    )

    outbound = route_blocker(session, blocker.id)
    # Should safely fallback to candidate 1 (Meera)
    assert outbound["member_id"] == m2.id


def test_b4_blocked_member_never_a_candidate(session: Session, sample_project: Project):
    m_blocked = Member(project_id=sample_project.id, name="Kabir", role="member", skills="everything python docker")
    m_other = Member(project_id=sample_project.id, name="Aarav", role="member", skills="none")
    session.add_all([m_blocked, m_other])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-7", owner_member_id=m_blocked.id)
    session.add(t)
    session.commit()

    blocker = Blocker(task_id=t.id, description="docker issue", needed_from="")
    session.add(blocker)
    session.commit()

    candidates = get_candidate_helpers(session, blocker)
    candidate_ids = [c.id for c in candidates]
    assert m_blocked.id not in candidate_ids


def test_b5_timeout_escalation_hop_with_event(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)

    m1 = Member(project_id=sample_project.id, name="Blocked", role="member")
    m2 = Member(project_id=sample_project.id, name="Helper1", role="member")
    m3 = Member(project_id=sample_project.id, name="Helper2", role="lead")
    session.add_all([m1, m2, m3])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-1", owner_member_id=m1.id, status="blocked")
    session.add(t)
    session.commit()

    blocker = Blocker(
        task_id=t.id,
        description="Help needed",
        status="routed",
        routed_to_member_id=m2.id,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5),  # 5 min ago (> 2 min demo timeout)
    )
    session.add(blocker)
    session.commit()

    # Check timeouts should trigger hop to m3
    escalations = check_blocker_timeouts(session, sample_project.id)
    assert len(escalations) == 1
    assert escalations[0]["member_id"] == m3.id

    # Verify blocker_routed event was emitted for this hop
    events = session.exec(
        select(Event).where(Event.type == "blocker_routed", Event.task_id == t.id)
    ).all()
    assert len(events) >= 1


def test_b6_all_decline_escalates_to_lead(session: Session, sample_project: Project, monkeypatch):
    m_blocked = Member(project_id=sample_project.id, name="Blocked", role="member")
    m_helper = Member(project_id=sample_project.id, name="Helper", role="member")
    m_lead = Member(project_id=sample_project.id, name="Lead", role="lead")
    session.add_all([m_blocked, m_helper, m_lead])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-1", owner_member_id=m_blocked.id, status="blocked")
    session.add(t)
    session.commit()

    blocker = Blocker(task_id=t.id, description="Help needed")
    session.add(blocker)
    session.commit()

    # Route initially
    route_blocker(session, blocker.id)

    # Helper declines
    resp = on_helper_response(session, blocker.id, member_id=m_helper.id, accepted=False)
    assert resp["status"] == "declined"
    # Status stays routed, lead notified
    session.refresh(blocker)
    assert blocker.status == "routed"
    assert blocker.routed_to_member_id == m_lead.id


def test_b7_i_can_help_then_resolved(session: Session, sample_project: Project):
    m_blocked = Member(project_id=sample_project.id, name="Kabir", role="member")
    m_helper = Member(project_id=sample_project.id, name="Meera", role="lead")
    session.add_all([m_blocked, m_helper])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-7", owner_member_id=m_blocked.id, status="blocked")
    session.add(t)
    session.commit()

    blocker = Blocker(task_id=t.id, description="waiting on credentials")
    session.add(blocker)
    session.commit()

    # Helper accepts
    accept_resp = on_helper_response(session, blocker.id, member_id=m_helper.id, accepted=True)
    assert accept_resp["status"] == "accepted"

    # Resolve blocker
    resolve_resp = resolve_blocker(session, blocker.id, by_member_id=m_helper.id)
    assert resolve_resp["status"] == "resolved"
    assert resolve_resp["notify_member_id"] == m_blocked.id

    session.refresh(blocker)
    session.refresh(t)
    assert blocker.status == "resolved"
    assert blocker.resolved_at is not None
    # Task should transition back to in_progress!
    assert t.status == "in_progress"

    # Events verified
    events = session.exec(select(Event).where(Event.task_id == t.id)).all()
    event_types = [e.type for e in events]
    assert "blocker_resolved" in event_types
    assert "status_changed" in event_types


def test_b8_resolve_twice_is_idempotent(session: Session, sample_project: Project):
    m = Member(project_id=sample_project.id, name="M")
    t = Task(project_id=sample_project.id, key="T-1", owner_member_id=m.id, status="blocked")
    session.add_all([m, t])
    session.commit()

    b = Blocker(task_id=t.id, description="desc")
    session.add(b)
    session.commit()

    r1 = resolve_blocker(session, b.id, by_member_id=m.id)
    assert r1["status"] == "resolved"

    # Second call
    r2 = resolve_blocker(session, b.id, by_member_id=m.id)
    assert r2["status"] == "already_resolved"
