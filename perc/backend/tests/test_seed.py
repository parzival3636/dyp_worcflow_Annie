import time
from sqlmodel import Session, select
from fastapi.testclient import TestClient

from backend.models import Project, Member, Task, Blocker, Contradiction, Block
from backend.seed_demo import seed_database


def test_seed_demo_idempotence_and_counts(session: Session, client: TestClient):
    start_time = time.time()
    # First seed
    seed_database(target_session=session)
    elapsed = time.time() - start_time
    assert elapsed < 10.0, f"Seed took {elapsed:.2f}s (must be < 10s)"

    # Verify initial row counts
    proj = session.exec(select(Project).where(Project.code == "DEMO01")).first()
    assert proj is not None

    members = session.exec(select(Member).where(Member.project_id == proj.id)).all()
    tasks = session.exec(select(Task).where(Task.project_id == proj.id)).all()
    blocks = session.exec(select(Block).where(Block.project_id == proj.id)).all()
    blockers = session.exec(select(Blocker).where(Blocker.status == "open")).all()
    contradictions = session.exec(select(Contradiction).where(Contradiction.project_id == proj.id, Contradiction.status == "open")).all()

    assert len(members) == 4
    assert len(tasks) == 14
    assert len(blocks) == 4
    assert any(b.oversize_flag for b in blocks)
    assert len(blockers) == 1
    assert blockers[0].description == "connected, but waiting for test credentials"
    assert len(contradictions) == 1

    # Second seed (idempotent run)
    seed_database(target_session=session)

    members_2 = session.exec(select(Member).where(Member.project_id == proj.id)).all()
    tasks_2 = session.exec(select(Task).where(Task.project_id == proj.id)).all()
    assert len(members_2) == 4
    assert len(tasks_2) == 14

    # Validate snapshot endpoint against seeded DEMO01
    resp = client.get("/api/projects/DEMO01/snapshot")
    assert resp.status_code == 200
    snap = resp.json()
    assert snap["project"]["code"] == "DEMO01"
    assert len(snap["members"]) == 4
    assert len(snap["tasks"]) == 14
    assert len(snap["blocks"]) == 4
    assert len(snap["contradictions"]) == 1
