import pytest
from sqlmodel import Session, select
from backend.models import Project, Task, Event
from backend.state import transition_task, IllegalTransition


def create_task(session: Session, project: Project, key: str, status: str = "todo") -> Task:
    task = Task(
        project_id=project.id,
        key=key,
        title=f"Task {key}",
        status=status,
        progress=0,
        risk="ok",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def test_s1_todo_to_in_progress(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S1", status="todo")
    assert task.started_at is None

    transition_task(
        session=session,
        task_key="T-S1",
        project_id=sample_project.id,
        new_status="in_progress",
        actor_member_id=1,
        reason="Started working",
        source="reply",
    )
    session.commit()
    session.refresh(task)

    assert task.status == "in_progress"
    assert task.started_at is not None

    events = session.exec(select(Event).where(Event.task_id == task.id)).all()
    assert len(events) == 1
    assert events[0].type == "status_changed"
    assert events[0].payload["from_status"] == "todo"
    assert events[0].payload["to_status"] == "in_progress"


def test_s2_in_progress_to_blocked_and_back(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S2", status="in_progress")

    # in_progress -> blocked
    transition_task(
        session=session,
        task_key="T-S2",
        project_id=sample_project.id,
        new_status="blocked",
        actor_member_id=2,
        reason="Waiting on API credentials",
        source="blocker",
    )
    session.commit()
    session.refresh(task)
    assert task.status == "blocked"

    # blocked -> in_progress
    transition_task(
        session=session,
        task_key="T-S2",
        project_id=sample_project.id,
        new_status="in_progress",
        actor_member_id=2,
        reason="Credentials received",
        source="blocker",
    )
    session.commit()
    session.refresh(task)
    assert task.status == "in_progress"

    events = session.exec(select(Event).where(Event.task_id == task.id)).all()
    assert len(events) == 2
    assert events[0].payload["to_status"] == "blocked"
    assert events[1].payload["to_status"] == "in_progress"


def test_s3_in_progress_to_claimed_done(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S3", status="in_progress")

    transition_task(
        session=session,
        task_key="T-S3",
        project_id=sample_project.id,
        new_status="claimed_done",
        actor_member_id=1,
        reason="Finished coding",
        source="reply",
    )
    session.commit()
    session.refresh(task)
    assert task.status == "claimed_done"


def test_s4_claimed_done_to_verified_done_with_reply_rejected(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S4", status="claimed_done")

    with pytest.raises(IllegalTransition):
        transition_task(
            session=session,
            task_key="T-S4",
            project_id=sample_project.id,
            new_status="verified_done",
            actor_member_id=1,
            reason="I am really done",
            source="reply",
        )


def test_s5_claimed_done_to_verified_done_with_verifier(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S5", status="claimed_done")
    assert task.completed_at is None
    assert task.progress == 0

    transition_task(
        session=session,
        task_key="T-S5",
        project_id=sample_project.id,
        new_status="verified_done",
        actor_member_id=None,
        reason="Automated test suite passed and matching commits found",
        source="verifier",
        extra={"verdict": "verified", "confidence": 0.95},
    )
    session.commit()
    session.refresh(task)

    assert task.status == "verified_done"
    assert task.completed_at is not None
    assert task.progress == 100


def test_s6_claimed_done_to_needs_review(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S6", status="claimed_done")

    transition_task(
        session=session,
        task_key="T-S6",
        project_id=sample_project.id,
        new_status="needs_review",
        actor_member_id=None,
        reason="Diff did not match all acceptance criteria",
        source="verifier",
        extra={"verdict": "partial", "confidence": 0.5},
    )
    session.commit()
    session.refresh(task)
    assert task.status == "needs_review"


def test_s7_needs_review_to_verified_done_with_lead_override(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S7", status="needs_review")

    transition_task(
        session=session,
        task_key="T-S7",
        project_id=sample_project.id,
        new_status="verified_done",
        actor_member_id=1,
        reason="Lead manually verified output",
        source="lead_override",
    )
    session.commit()
    session.refresh(task)
    assert task.status == "verified_done"
    assert task.progress == 100


def test_s8_needs_review_to_verified_done_with_verifier_rejected(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S8", status="needs_review")

    with pytest.raises(IllegalTransition):
        transition_task(
            session=session,
            task_key="T-S8",
            project_id=sample_project.id,
            new_status="verified_done",
            actor_member_id=None,
            reason="Verifier cannot directly jump from needs_review to verified_done",
            source="verifier",
            extra={"verdict": "verified", "confidence": 0.9},
        )


def test_s9_verified_done_to_in_progress_by_lead(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S9", status="verified_done")

    transition_task(
        session=session,
        task_key="T-S9",
        project_id=sample_project.id,
        new_status="in_progress",
        actor_member_id=1,
        reason="Lead reopened task due to regression",
        source="lead_override",
    )
    session.commit()
    session.refresh(task)
    assert task.status == "in_progress"


def test_s10_todo_to_verified_done_rejected(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S10", status="todo")

    with pytest.raises(IllegalTransition):
        transition_task(
            session=session,
            task_key="T-S10",
            project_id=sample_project.id,
            new_status="verified_done",
            actor_member_id=1,
            reason="Direct jump is illegal",
            source="lead_override",
        )


def test_s11_same_status_twice_is_noop(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S11", status="in_progress")

    transition_task(
        session=session,
        task_key="T-S11",
        project_id=sample_project.id,
        new_status="in_progress",
        actor_member_id=1,
        reason="Redundant call",
        source="reply",
    )
    session.commit()

    events = session.exec(select(Event).where(Event.task_id == task.id)).all()
    assert len(events) == 0


def test_s12_rollback_leaves_neither_status_nor_event_changed(session: Session, sample_project: Project):
    task = create_task(session, sample_project, "T-S12", status="todo")

    try:
        transition_task(
            session=session,
            task_key="T-S12",
            project_id=sample_project.id,
            new_status="in_progress",
            actor_member_id=1,
            reason="Will fail and rollback",
            source="reply",
        )
        raise RuntimeError("Simulated failure mid-transaction")
    except RuntimeError:
        session.rollback()

    session.refresh(task)
    assert task.status == "todo"
    events = session.exec(select(Event).where(Event.task_id == task.id)).all()
    assert len(events) == 0
