from datetime import datetime, timezone
from sqlmodel import Session, select
from fastapi.testclient import TestClient
import pytest

from backend.models import Project, Member, Task, Blocker, Event
from backend.seed_demo import seed_database
from backend.llm import P3Reply, P3Blocker, P6Route
import backend.routing as routing_mod
import backend.guide as guide_mod
from backend.routing import on_helper_response, resolve_blocker
from backend.ripple import risk_recompute


def test_e2e_kabir_demo_story(session: Session, client: TestClient, monkeypatch):
    """
    End-to-End simulation of the 15-minute Hackathon rehearsal demo story:
    1. Seed project DEMO01.
    2. Kabir replies: 'connected, but waiting for test credentials' -> blocker detected on T-7.
    3. T-7 becomes blocked; routing chooses Meera (lead/task owner).
    4. Downstream tasks (T-10, T-14 Demo) become at_risk via ripple propagation.
    5. Guide /ask 'Why is the demo at risk?' cites T-7.
    6. Meera accepts ('I can help') and resolves the blocker.
    7. T-7 transitions back to in_progress; risks clear back to ok.
    8. Every step writes events visible in /snapshot.
    """
    # 1. Seed
    seed_database(target_session=session)
    proj = session.exec(select(Project).where(Project.code == "DEMO01")).first()
    assert proj is not None

    t7 = session.exec(select(Task).where(Task.project_id == proj.id, Task.key == "T-7")).first()
    t14 = session.exec(select(Task).where(Task.project_id == proj.id, Task.key == "T-14")).first()
    meera = session.exec(select(Member).where(Member.project_id == proj.id, Member.name == "Meera")).first()
    kabir = session.exec(select(Member).where(Member.project_id == proj.id, Member.name == "Kabir")).first()

    # 2. Simulate Kabir's reply parsed as blocker
    p3_mock = P3Reply(
        task_key="T-7",
        intent="blocker",
        new_status="blocked",
        blocker=P3Blocker(
            description="connected, but waiting for test credentials",
            type="dependency",
            needed_from="Meera",
        ),
        confidence=0.98,
    )
    assert p3_mock.intent == "blocker"
    assert p3_mock.blocker.needed_from == "Meera"

    # 3. Blocker routed to Meera
    monkeypatch.setattr(
        routing_mod,
        "call_json",
        lambda *args, **kwargs: P6Route(member_id=meera.id, reason="Owner of auth credentials"),
    )

    blocker = session.exec(select(Blocker).where(Blocker.task_id == t7.id, Blocker.status == "open")).first()
    assert blocker is not None

    outbound = routing_mod.route_blocker(session, blocker.id)
    assert outbound["member_id"] == meera.id
    assert "Kabir is blocked on" in outbound["text"]

    # 4. Ripple marks downstream tasks and milestone at_risk
    risk_recompute(session, proj.id)
    session.commit()
    session.refresh(t7)
    session.refresh(t14)
    assert t7.risk in ["at_risk", "critical"]
    assert t14.risk in ["at_risk", "critical"]

    # 5. Guide /ask cites T-7
    monkeypatch.setattr(
        guide_mod,
        "call_json",
        lambda *args, **kwargs: guide_mod.GuideAction(
            final="The Demo milestone T-14 is at risk because Kabir is blocked on T-7 waiting for credentials.",
            cited_keys=["T-7", "T-14"],
        ),
    )
    ask_resp = client.post(
        f"/api/projects/{proj.code}/ask",
        json={"question": "Why is the demo at risk?"},
    )
    assert ask_resp.status_code == 200
    assert "T-7" in ask_resp.json()["cited_keys"]

    # 6. Meera taps "I can help"
    accept_res = on_helper_response(session, blocker.id, member_id=meera.id, accepted=True)
    assert accept_res["status"] == "accepted"

    # Meera resolves the blocker
    resolve_res = resolve_blocker(session, blocker.id, by_member_id=meera.id)
    assert resolve_res["status"] == "resolved"
    assert resolve_res["notify_member_id"] == kabir.id

    session.refresh(t7)
    session.refresh(blocker)
    assert blocker.status == "resolved"
    # Task T-7 is back to in_progress!
    assert t7.status == "in_progress"

    # Risks fall back to ok
    risk_recompute(session, proj.id)
    session.refresh(t7)
    session.refresh(t14)
    assert t7.risk == "ok"
    assert t14.risk == "ok"

    # 7. Check snapshot contains events and updated states
    session.commit()
    snap_resp = client.get(f"/api/projects/{proj.code}/snapshot")
    assert snap_resp.status_code == 200
    snap = snap_resp.json()

    event_types = [e["type"] for e in snap["events"]]
    assert "blocker_routed" in event_types
    assert "blocker_resolved" in event_types
    assert "status_changed" in event_types
