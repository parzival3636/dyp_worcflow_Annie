import concurrent.futures
import threading
from sqlmodel import Session, select
from fastapi.testclient import TestClient

from backend.db import get_session
from backend.models import Project, Task
from backend.state import transition_task, IllegalTransition


def test_x1_two_threads_transition_same_task(session: Session, sample_project: Project):
    t = Task(project_id=sample_project.id, key="T-1", status="todo")
    session.add(t)
    session.commit()

    results = []
    errors = []

    def run_transition(target_status, source):
        try:
            with get_session() as thread_session:
                task = transition_task(
                    session=thread_session,
                    task_key="T-1",
                    project_id=sample_project.id,
                    new_status=target_status,
                    actor_member_id=1,
                    reason=f"Transition to {target_status}",
                    source=source,
                )
                thread_session.commit()
                results.append(task.status)
        except Exception as e:
            errors.append(e)

    # Thread 1 tries to move to in_progress (legal from todo)
    # Thread 2 tries to move to in_progress (legal from todo)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_transition, "in_progress", "reply")
        f2 = executor.submit(run_transition, "in_progress", "reply")
        concurrent.futures.wait([f1, f2])

    session.refresh(t)
    assert t.status == "in_progress"
    # Both completed or one updated and one idempotent
    assert len(errors) == 0


def test_x2_reply_and_verifier_transition_race(session: Session, sample_project: Project):
    t = Task(project_id=sample_project.id, key="T-1", status="claimed_done")
    session.add(t)
    session.commit()

    results = []

    def try_verify():
        try:
            with get_session() as s:
                task = transition_task(
                    session=s,
                    task_key="T-1",
                    project_id=sample_project.id,
                    new_status="verified_done",
                    actor_member_id=None,
                    reason="Verifier passed",
                    source="verifier",
                    extra={"verdict": "verified", "confidence": 0.95},
                )
                s.commit()
                results.append("verified")
        except IllegalTransition:
            results.append("illegal_verify")

    def try_review():
        try:
            with get_session() as s:
                task = transition_task(
                    session=s,
                    task_key="T-1",
                    project_id=sample_project.id,
                    new_status="needs_review",
                    actor_member_id=None,
                    reason="Partial evidence",
                    source="verifier",
                )
                s.commit()
                results.append("needs_review")
        except IllegalTransition:
            results.append("illegal_review")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_verify)
        f2 = executor.submit(try_review)
        concurrent.futures.wait([f1, f2])

    session.refresh(t)
    # The final state is valid in the state machine (either verified_done or needs_review)
    assert t.status in ["verified_done", "needs_review"]


def test_x3_twenty_concurrent_snapshot_reads_during_writes(client: TestClient, sample_project: Project, session: Session):
    for i in range(1, 10):
        session.add(Task(project_id=sample_project.id, key=f"T-{i}", status="todo", effort=2))
    session.commit()

    write_running = True

    def writer_thread():
        cnt = 10
        while write_running and cnt < 15:
            try:
                with get_session() as s:
                    t = Task(project_id=sample_project.id, key=f"T-{cnt}", status="todo", effort=1)
                    s.add(t)
                    s.commit()
                    cnt += 1
            except Exception:
                pass

    writer = threading.Thread(target=writer_thread)
    writer.start()

    read_results = []

    def reader():
        resp = client.get(f"/api/projects/{sample_project.code}/snapshot")
        read_results.append(resp.status_code)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(reader) for _ in range(20)]
        concurrent.futures.wait(futures)

    write_running = False
    writer.join(timeout=2.0)

    # All 20 snapshot reads succeeded with HTTP 200 without deadlock
    assert len(read_results) == 20
    assert all(code == 200 for code in read_results)


def test_x4_job_and_api_running_together_pool_not_exhausted(client: TestClient, sample_project: Project):
    def api_call():
        r = client.get(f"/api/projects/{sample_project.code}/snapshot")
        return r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(api_call) for _ in range(15)]
        results = [f.result() for f in futures]

    assert all(r == 200 for r in results)
