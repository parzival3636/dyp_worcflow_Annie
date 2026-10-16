import time
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.models import Project, Member, Task, TaskDep, Event
from backend.llm import P2Task, P2Plan, PlanGenerationError
import backend.planner as planner_module


def test_a1_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"telegram", "github", "llm", "db"}
    assert data["db"] == "ok"


def test_a2_snapshot_contract_schema(client: TestClient):
    response = client.get("/api/projects/DEMO01/snapshot")
    assert response.status_code == 200
    data = response.json()

    required_keys = {
        "project",
        "members",
        "blocks",
        "tasks",
        "deps",
        "events",
        "contradictions",
        "contributions",
        "guide_notes",
    }
    assert required_keys.issubset(data.keys())

    proj = data["project"]
    for field in ("code", "name", "status", "repo_url", "starts_at", "ends_at"):
        assert field in proj, f"Missing project field: {field}"

    members = data["members"]
    assert len(members) >= 1
    for m in members:
        for field in ("id", "name", "role", "github_login", "invite_status", "color"):
            assert field in m, f"Missing member field: {field}"

    tasks = data["tasks"]
    assert len(tasks) >= 1
    for t in tasks:
        for field in (
            "key",
            "title",
            "status",
            "owner_member_id",
            "block_id",
            "deadline",
            "progress",
            "risk",
            "is_milestone",
            "acceptance_criteria",
            "description",
            "verification",
            "blocker",
        ):
            assert field in t, f"Missing task field: {field}"


def test_a3_snapshot_unknown_code(client: TestClient):
    response = client.get("/api/projects/NONEXISTENT_XYZ_123/snapshot")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "code" in data
    assert data["code"] == "PROJECT_NOT_FOUND"


def test_a4_snapshot_performance_under_300ms(client: TestClient, session: Session):
    # Seed 20 tasks in DB for a project
    project = Project(code="PERF01", name="Perf Test Project", status="running")
    session.add(project)
    session.commit()
    session.refresh(project)

    for i in range(1, 21):
        task = Task(
            project_id=project.id,
            key=f"T-{i}",
            title=f"Perf Task {i}",
            status="in_progress" if i % 2 == 0 else "todo",
            progress=50 if i % 2 == 0 else 0,
            effort=2,
            is_milestone=(i == 20),
        )
        session.add(task)
    session.commit()

    start_time = time.time()
    response = client.get(f"/api/projects/{project.code}/snapshot")
    elapsed_ms = (time.time() - start_time) * 1000

    assert response.status_code == 200
    assert len(response.json()["tasks"]) == 20
    assert elapsed_ms < 300, f"Snapshot took {elapsed_ms:.2f} ms (expected < 300 ms)"


def test_a5_post_plan_with_mocked_llm(client: TestClient, sample_project: Project, monkeypatch):
    mock_p2_tasks = [
        P2Task(title=f"Task {i}", description="desc", acceptance_criteria=["ac"], effort=2)
        for i in range(1, 15)
    ]
    monkeypatch.setattr(
        planner_module,
        "call_json",
        lambda *args, **kwargs: P2Plan(tasks=mock_p2_tasks),
    )

    response = client.post(
        f"/api/projects/{sample_project.code}/plan",
        json={"idea": "Build Pilot AI", "team_size": 4, "skills": ["python", "fastapi"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_count"] == 14
    assert len(data["tasks"]) == 14


def test_a6_post_plan_llm_failure_returns_friendly_502(client: TestClient, sample_project: Project, session: Session, monkeypatch):
    def raise_fail(*args, **kwargs):
        raise PlanGenerationError("API quota exceeded")

    monkeypatch.setattr(planner_module, "call_json", raise_fail)

    response = client.post(
        f"/api/projects/{sample_project.code}/plan",
        json={"idea": "Failing project"},
    )
    assert response.status_code == 502
    data = response.json()
    assert data["code"] == "PLAN_GENERATION_FAILED"
    # Ensure no partial tasks created
    tasks = session.exec(select(Task).where(Task.project_id == sample_project.id)).all()
    assert len(tasks) == 0


def test_a7_post_bundle_then_confirm_assignment(client: TestClient, sample_project: Project, session: Session):
    # Setup members and tasks
    m1 = Member(project_id=sample_project.id, name="Alice", role="lead")
    m2 = Member(project_id=sample_project.id, name="Bob", role="member")
    t1 = Task(project_id=sample_project.id, key="T-1", title="Task 1", effort=3)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Task 2", effort=4)
    session.add_all([m1, m2, t1, t2])
    session.commit()

    # Bundle endpoint
    bundle_resp = client.post(f"/api/projects/{sample_project.code}/bundle")
    assert bundle_resp.status_code == 200

    # Confirm assignment endpoint
    confirm_resp = client.post(f"/api/projects/{sample_project.code}/confirm-assignment")
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


def test_a8_patch_task_deps_cycle_returns_422(client: TestClient, sample_project: Project, session: Session):
    t1 = Task(project_id=sample_project.id, key="T-1", title="Task 1", effort=2)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Task 2", effort=2)
    session.add_all([t1, t2])
    session.commit()

    # T2 depends on T1
    dep = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="hard")
    session.add(dep)
    session.commit()

    # Attempting to make T1 depend on T2 creates cycle T1 -> T2 -> T1
    response = client.patch(
        f"/api/projects/{sample_project.code}/tasks/T-1",
        json={"depends_on_keys": ["T-2"]},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "DEPENDENCY_CYCLE"


def test_a9_delete_task_removes_edges_and_writes_event(client: TestClient, sample_project: Project, session: Session):
    t1 = Task(project_id=sample_project.id, key="T-1", title="To Delete", effort=2)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Survivor", effort=2)
    session.add_all([t1, t2])
    session.commit()

    dep = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="hard")
    session.add(dep)
    session.commit()

    t1_id = t1.id
    resp = client.delete(f"/api/projects/{sample_project.code}/tasks/T-1")
    assert resp.status_code == 200

    # Verify task and dep deleted
    deleted_task = session.exec(select(Task).where(Task.key == "T-1")).first()
    assert deleted_task is None

    edges = session.exec(select(TaskDep).where(TaskDep.depends_on_task_id == t1_id)).all()
    assert len(edges) == 0

    # Event written
    events = session.exec(select(Event).where(Event.project_id == sample_project.id)).all()
    assert any(e.payload.get("action") == "deleted" for e in events)


def test_a10_override_verify_by_lead(client: TestClient, sample_project: Project, session: Session):
    m = Member(project_id=sample_project.id, name="Lead", role="lead")
    session.add(m)
    session.commit()
    session.refresh(m)
    sample_project.lead_member_id = m.id
    session.add(sample_project)

    t = Task(project_id=sample_project.id, key="T-1", title="Needs Review Task", status="needs_review", effort=3)
    session.add(t)
    session.commit()

    resp = client.post(f"/api/projects/{sample_project.code}/tasks/T-1/override-verify")
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified_done"

    session.refresh(t)
    assert t.status == "verified_done"
    assert t.progress == 100


def test_a13_get_events_pagination(client: TestClient, sample_project: Project, session: Session):
    for i in range(1, 16):
        session.add(
            Event(
                project_id=sample_project.id,
                type="guide_note",
                payload={"note": f"Note {i}"},
            )
        )
    session.commit()

    resp = client.get(f"/api/projects/{sample_project.code}/events?limit=5&offset=5")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 5


def test_a11_ask_endpoint(client: TestClient, sample_project: Project, monkeypatch):
    import backend.guide as guide_mod
    monkeypatch.setattr(
        guide_mod,
        "call_json",
        lambda *args, **kwargs: guide_mod.GuideAction(final="Task T-1 was verified.", cited_keys=["T-1"]),
    )

    resp = client.post(
        f"/api/projects/{sample_project.code}/ask",
        json={"question": "What is the status of T-1?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "T-1" in data["cited_keys"]


def test_a12_report_endpoint_and_cors(client: TestClient, sample_project: Project):
    # Test report
    resp = client.post(f"/api/projects/{sample_project.code}/report")
    assert resp.status_code == 200
    report = resp.json()
    assert "project_code" in report
    assert "counts" in report
    assert "member_contributions" in report

    # Test CORS headers on OPTIONS
    cors_resp = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert cors_resp.status_code == 200
    assert "access-control-allow-origin" in cors_resp.headers

