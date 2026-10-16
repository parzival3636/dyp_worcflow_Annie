from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
import pytest

from backend.models import Project, Member, Task, CommitLog, Blocker, Contradiction, Event
import backend.guide as guide_module
from backend.guide import (
    GuideAction,
    run_guide_query,
    guide_tick,
    generate_report,
    get_member_contributions,
    get_timeline,
    get_task,
    get_risks,
)


def test_g1_tool_loop_hits_6_steps_and_stops(session: Session, sample_project: Project, monkeypatch):
    calls = 0

    def mock_call_json(*args, **kwargs):
        nonlocal calls
        calls += 1
        # Always request another tool
        return GuideAction(tool="get_project_snapshot", args={})

    monkeypatch.setattr(guide_module, "call_json", mock_call_json)

    result = run_guide_query(session, sample_project.id, "Infinite loop test", max_steps=6)
    assert result["steps"] == 6
    assert result["answer"] is not None


def test_g2_json_action_loop_without_native_tools(session: Session, sample_project: Project, monkeypatch):
    t = Task(project_id=sample_project.id, key="T-1", title="Init Project", status="verified_done")
    session.add(t)
    session.commit()

    step = 0

    def mock_call_json(*args, **kwargs):
        nonlocal step
        step += 1
        if step == 1:
            return GuideAction(tool="get_task", args={"key": "T-1"})
        else:
            return GuideAction(final="Task T-1 is verified_done and ready.")

    monkeypatch.setattr(guide_module, "call_json", mock_call_json)

    result = run_guide_query(session, sample_project.id, "What is status of T-1?")
    assert "T-1" in result["answer"]
    assert "T-1" in result["cited_keys"]


def test_g3_invented_sha_rejected_and_retried(session: Session, sample_project: Project, monkeypatch):
    step = 0
    received_prompts = []

    def mock_call_json(system, prompt, model_cls, *args, **kwargs):
        nonlocal step
        step += 1
        received_prompts.append(prompt)
        if step == 1:
            # Model hallucinated SHA deadbeef123 that never appeared in tool results
            return GuideAction(final="I found commit deadbeef123 did everything.")
        else:
            # Model corrected itself on retry
            return GuideAction(final="I have no evidence of any commits.")

    monkeypatch.setattr(guide_module, "call_json", mock_call_json)

    result = run_guide_query(session, sample_project.id, "Which commit completed T-1?")
    assert step == 2
    assert "rejected because you cited items that NEVER appeared" in received_prompts[1]


def test_g4_who_contributed_what_matches_commit_log(session: Session, sample_project: Project):
    m = Member(project_id=sample_project.id, name="Meera", role="lead")
    session.add(m)
    session.commit()
    session.refresh(m)

    c1 = CommitLog(
        sha="a1b2c3d",
        project_id=sample_project.id,
        author_login="meera",
        member_id=m.id,
        message="Initial commit",
        additions=120,
        deletions=20,
        committed_at=datetime.now(timezone.utc),
    )
    c2 = CommitLog(
        sha="e4f5g6h",
        project_id=sample_project.id,
        author_login="meera",
        member_id=m.id,
        message="Add models",
        additions=60,
        deletions=10,
        committed_at=datetime.now(timezone.utc),
    )
    session.add_all([c1, c2])
    session.commit()

    contrib = get_member_contributions(session, sample_project.id, "Meera")
    assert contrib["commit_count"] == 2
    assert contrib["total_lines_changed"] == (140 + 70)


def test_g5_what_was_completed_by_time(session: Session, sample_project: Project):
    t1 = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Completed Early",
        status="verified_done",
        completed_at=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc),
    )
    t2 = Task(
        project_id=sample_project.id,
        key="T-2",
        title="Completed Late",
        status="verified_done",
        completed_at=datetime(2026, 10, 16, 16, 0, tzinfo=timezone.utc),
    )
    session.add_all([t1, t2])
    session.commit()

    timeline = get_timeline(session, sample_project.id, "2026-10-16T12:00:00Z")
    assert timeline["completed_count"] == 1
    assert timeline["completed_tasks"][0]["key"] == "T-1"


def test_g6_why_is_demo_at_risk_cites_blocked_task(session: Session, sample_project: Project):
    t_blocked = Task(
        project_id=sample_project.id,
        key="T-7",
        title="Payment Gateway",
        status="blocked",
        risk="critical",
    )
    demo_milestone = Task(
        project_id=sample_project.id,
        key="T-14",
        title="Demo Milestone",
        is_milestone=True,
        risk="critical",
    )
    session.add_all([t_blocked, demo_milestone])
    session.commit()

    risks = get_risks(session, sample_project.id)
    assert risks["milestone_risk"] == "critical"
    assert any(t["key"] == "T-7" for t in risks["at_risk_tasks"])


def test_g7_proactive_tick_twice_in_5_min_no_duplicates(session: Session, sample_project: Project):
    past_deadline = datetime.now(timezone.utc) - timedelta(hours=2)
    t_overdue = Task(
        project_id=sample_project.id,
        key="T-5",
        title="Overdue Feature",
        status="in_progress",
        deadline=past_deadline,
    )
    session.add(t_overdue)
    session.commit()

    first_tick = guide_tick(session, sample_project.id)
    assert len(first_tick) >= 1
    session.commit()

    # Second tick immediately after
    second_tick = guide_tick(session, sample_project.id)
    assert len(second_tick) == 0


def test_g8_unknown_member_or_task_reports_no_data(session: Session, sample_project: Project):
    member_res = get_member_contributions(session, sample_project.id, "NonexistentMember")
    assert "error" in member_res

    task_res = get_task(session, sample_project.id, "T-999")
    assert "error" in task_res
