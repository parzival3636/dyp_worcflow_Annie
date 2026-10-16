from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
import pytest

from backend.models import Project, Member, Task, TaskDep, Blocker, Event
from backend.ripple import risk_recompute, ripple_caption


def test_r1_no_blocked_or_late_tasks_all_ok(session: Session, sample_project: Project):
    t1 = Task(project_id=sample_project.id, key="T-1", title="Task 1", effort=2, risk="ok")
    t2 = Task(project_id=sample_project.id, key="T-2", title="Task 2", effort=3, risk="ok")
    session.add_all([t1, t2])
    session.commit()

    res = risk_recompute(session, sample_project.id)
    session.refresh(t1)
    session.refresh(t2)

    assert t1.risk == "ok"
    assert t2.risk == "ok"


def test_r2_t7_blocked_downstream_at_risk_or_critical(session: Session, sample_project: Project):
    now = datetime.now(timezone.utc)
    t7 = Task(
        project_id=sample_project.id,
        key="T-7",
        title="Blocked Task",
        status="blocked",
        deadline=now + timedelta(hours=4),
        effort=2,
    )
    t8 = Task(
        project_id=sample_project.id,
        key="T-8",
        title="Downstream Task",
        status="todo",
        deadline=now + timedelta(hours=6),  # slack ~ 2h
        effort=2,
    )
    session.add_all([t7, t8])
    session.commit()

    # t8 depends on t7
    dep = TaskDep(task_id=t8.id, depends_on_task_id=t7.id, kind="hard")
    session.add(dep)

    # Blocker created 6 hours ago (slip = 6h)
    blocker = Blocker(
        task_id=t7.id,
        description="Blocked on API",
        created_at=now - timedelta(hours=6),
    )
    session.add(blocker)
    session.commit()

    risk_recompute(session, sample_project.id)
    session.refresh(t8)

    # Downstream task should become at_risk or critical
    assert t8.risk in ["at_risk", "critical"]


def test_r3_slip_smaller_than_half_slack_is_ok(session: Session, sample_project: Project):
    now = datetime.now(timezone.utc)
    t1 = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Minor Delay",
        status="blocked",
        deadline=now + timedelta(hours=10),
        effort=1,
    )
    t2 = Task(
        project_id=sample_project.id,
        key="T-2",
        title="Generous Slack",
        status="todo",
        deadline=now + timedelta(hours=30),  # Slack is 20 hours!
        effort=1,
    )
    session.add_all([t1, t2])
    session.commit()

    dep = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="hard")
    session.add(dep)

    # Small slip of 1 hour (< 0.5 * 20)
    blocker = Blocker(
        task_id=t1.id,
        description="Quick issue",
        created_at=now - timedelta(hours=1),
    )
    session.add(blocker)
    session.commit()

    risk_recompute(session, sample_project.id)
    session.refresh(t2)
    assert t2.risk == "ok"


def test_r4_slip_greater_than_slack_deadline_within_12h_is_critical(session: Session, sample_project: Project):
    now = datetime.now(timezone.utc)
    # Task deadline is 6 hours from now, slip is 8 hours
    t = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Critical Task",
        status="blocked",
        deadline=now + timedelta(hours=6),
        effort=2,
    )
    session.add(t)
    session.commit()

    blocker = Blocker(
        task_id=t.id,
        description="Huge blocker",
        created_at=now - timedelta(hours=8),
    )
    session.add(blocker)
    session.commit()

    risk_recompute(session, sample_project.id)
    session.refresh(t)
    assert t.risk == "critical"


def test_r5_milestone_worst_risk_among_predecessors(session: Session, sample_project: Project):
    now = datetime.now(timezone.utc)
    t_crit = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Predecessor Task",
        status="blocked",
        deadline=now + timedelta(hours=4),
        effort=2,
    )
    t_mile = Task(
        project_id=sample_project.id,
        key="T-Demo",
        title="Final Demo",
        is_milestone=True,
        deadline=now + timedelta(hours=6),
        effort=1,
    )
    session.add_all([t_crit, t_mile])
    session.commit()

    blocker = Blocker(task_id=t_crit.id, description="Severe blocker", created_at=now - timedelta(hours=8))
    session.add(blocker)

    dep = TaskDep(task_id=t_mile.id, depends_on_task_id=t_crit.id, kind="hard")
    session.add(dep)
    session.commit()

    risk_recompute(session, sample_project.id)
    session.refresh(t_crit)
    session.refresh(t_mile)
    # Milestone inherits critical risk from t_crit
    assert t_crit.risk == "critical"
    assert t_mile.risk == "critical"


def test_r6_blocker_resolved_risks_fall_back_to_ok(session: Session, sample_project: Project):
    t = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Recovering Task",
        status="in_progress",  # Blocker was resolved
        risk="critical",
    )
    session.add(t)
    session.commit()

    risk_recompute(session, sample_project.id)
    session.refresh(t)
    assert t.risk == "ok"

    events = session.exec(
        select(Event).where(Event.project_id == sample_project.id, Event.type == "risk_changed")
    ).all()
    assert len(events) >= 1
    assert events[-1].payload["new_risk"] == "ok"


def test_r7_verified_done_task_always_ok(session: Session, sample_project: Project):
    past = datetime.now(timezone.utc) - timedelta(days=2)
    t = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Done Task",
        status="verified_done",
        deadline=past,  # past deadline but verified!
        risk="at_risk",
    )
    session.add(t)
    session.commit()

    risk_recompute(session, sample_project.id)
    session.refresh(t)
    assert t.risk == "ok"


def test_r8_recompute_twice_with_no_change_is_idempotent(session: Session, sample_project: Project):
    t = Task(project_id=sample_project.id, key="T-1", title="Task", risk="ok")
    session.add(t)
    session.commit()

    r1 = risk_recompute(session, sample_project.id)
    r2 = risk_recompute(session, sample_project.id)
    assert r2["changes"] == 0

    events = session.exec(select(Event).where(Event.type == "risk_changed")).all()
    assert len(events) == 0


def test_r9_ripple_caption_contains_owner_key_and_milestone(session: Session, sample_project: Project):
    m = Member(project_id=sample_project.id, name="Kabir")
    session.add(m)
    session.commit()

    t7 = Task(
        project_id=sample_project.id,
        key="T-7",
        title="Stripe API",
        status="blocked",
        owner_member_id=m.id,
    )
    demo = Task(
        project_id=sample_project.id,
        key="T-14",
        title="Demo Pitch",
        is_milestone=True,
        risk="at_risk",
    )
    session.add_all([t7, demo])
    session.commit()

    caption = ripple_caption(session, sample_project.id)
    assert "Kabir" in caption
    assert "T-7" in caption
    assert "Demo Pitch" in caption
