from datetime import datetime, timezone
from sqlmodel import Session, select
import pytest

from backend.models import Project, Member, Task, Message, Verification, Contradiction, Event
from backend.llm import P5Contradiction
import backend.contradiction as contradiction_module
from backend.contradiction import (
    check_contradictions,
    resolve_contradiction,
    create_contradiction,
)


def test_c1_rule1_member_claims_done_while_owner_blocked(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(
        contradiction_module,
        "call_json",
        lambda *args, **kwargs: P5Contradiction(has_contradiction=False),
    )

    m_meera = Member(project_id=sample_project.id, name="Meera", role="lead")
    m_kabir = Member(project_id=sample_project.id, name="Kabir", role="member")
    session.add_all([m_meera, m_kabir])
    session.commit()

    t7 = Task(
        project_id=sample_project.id,
        key="T-7",
        title="Integration",
        status="blocked",
        owner_member_id=m_kabir.id,
    )
    session.add(t7)
    session.commit()

    # Meera sends message claiming integration is done
    msg = Message(
        project_id=sample_project.id,
        member_id=m_meera.id,
        direction="in",
        text="Integration is done!",
        parsed_json={"claims_about_others": ["Integration is done!"]},
    )
    session.add(msg)
    session.commit()

    outbound = check_contradictions(session, sample_project.id)
    assert len(outbound) == 2  # Question to Meera and question to Kabir

    contradictions = session.exec(select(Contradiction).where(Contradiction.project_id == sample_project.id)).all()
    assert len(contradictions) == 1
    assert "T-7" in contradictions[0].task_ids


def test_c2_rule2_opposite_status_on_shared_item(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(
        contradiction_module,
        "call_json",
        lambda *args, **kwargs: P5Contradiction(has_contradiction=False),
    )

    m1 = Member(project_id=sample_project.id, name="M1")
    m2 = Member(project_id=sample_project.id, name="M2")
    session.add_all([m1, m2])
    session.commit()

    t = Task(project_id=sample_project.id, key="T-3", title="Shared Database", status="blocked", owner_member_id=m1.id)
    session.add(t)
    session.commit()

    # M2 claims T-3 is done
    msg = Message(
        project_id=sample_project.id,
        member_id=m2.id,
        direction="in",
        text="T-3 is done",
        parsed_json={"claims_about_others": ["T-3 is done"]},
    )
    session.add(msg)
    session.commit()

    outbound = check_contradictions(session, sample_project.id)
    assert len(outbound) == 2


def test_c3_rule3_claimed_done_with_no_evidence(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(
        contradiction_module,
        "call_json",
        lambda *args, **kwargs: P5Contradiction(has_contradiction=False),
    )

    t = Task(project_id=sample_project.id, key="T-5", title="Verifier Target", status="claimed_done")
    session.add(t)
    session.commit()

    v = Verification(
        task_id=t.id,
        verdict="no_evidence",
        confidence=0.0,
        reason="No commits found",
    )
    session.add(v)
    session.commit()

    outbound = check_contradictions(session, sample_project.id)
    assert len(outbound) >= 1
    assert "no evidence" in outbound[0]["text"]

    c = session.exec(select(Contradiction).where(Contradiction.project_id == sample_project.id)).first()
    assert c is not None
    assert "T-5" in c.task_ids


def test_c4_llm_returns_no_contradiction_yields_none(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(
        contradiction_module,
        "call_json",
        lambda *args, **kwargs: P5Contradiction(has_contradiction=False),
    )

    outbound = check_contradictions(session, sample_project.id)
    assert len(outbound) == 0

    c = session.exec(select(Contradiction).where(Contradiction.project_id == sample_project.id)).all()
    assert len(c) == 0


def test_c5_duplicate_detection_run_twice_inserts_one_row_only(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(
        contradiction_module,
        "call_json",
        lambda *args, **kwargs: P5Contradiction(has_contradiction=False),
    )

    t = Task(project_id=sample_project.id, key="T-1", status="claimed_done")
    session.add(t)
    session.commit()

    v = Verification(task_id=t.id, verdict="no_evidence")
    session.add(v)
    session.commit()

    # First run
    check_contradictions(session, sample_project.id)
    # Second run immediately
    check_contradictions(session, sample_project.id)

    rows = session.exec(select(Contradiction).where(Contradiction.project_id == sample_project.id)).all()
    assert len(rows) == 1


def test_c6_contradiction_resolution_by_agreeing_evidence(session: Session, sample_project: Project):
    c = create_contradiction(
        session=session,
        project_id=sample_project.id,
        task_ids=["T-7"],
        member_ids=[1, 2],
        summary="Conflicting claims on T-7",
    )
    session.commit()

    res = resolve_contradiction(session, c.id, resolution="Resolved: commit sha 123 verified the API")
    session.refresh(c)

    assert c.status == "resolved"
    assert c.resolved_at is not None
    assert "commit sha 123" in c.resolution

    events = session.exec(
        select(Event).where(Event.project_id == sample_project.id, Event.type == "contradiction_resolved")
    ).all()
    assert len(events) == 1


def test_c7_outbound_messages_generated_with_questions(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(
        contradiction_module,
        "call_json",
        lambda *args, **kwargs: P5Contradiction(
            has_contradiction=True,
            summary="LLM detected conflict",
            task_ids=["T-2", "T-4"],
            member_ids=[1, 2],
            questions_to_ask=["Question for Meera", "Question for Kabir"],
        ),
    )

    outbound = check_contradictions(session, sample_project.id)
    assert len(outbound) == 2
    assert outbound[0]["member_id"] == 1
    assert outbound[0]["text"] == "Question for Meera"
    assert outbound[1]["member_id"] == 2
    assert outbound[1]["text"] == "Question for Kabir"
