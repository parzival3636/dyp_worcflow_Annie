import sys
import os
import argparse
from datetime import datetime, timezone, timedelta

# Ensure repo root is on sys.path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, SQLModel
from backend.db import engine, get_session
from backend.models import (
    Project,
    Member,
    Block,
    Task,
    TaskDep,
    Message,
    Blocker,
    Contradiction,
    Verification,
    CommitLog,
    Event,
)
from backend.events import add_event
from backend.ripple import risk_recompute


def seed_database(force: bool = False, target_session: Session = None):
    """
    Seeds the DEMO01 project with 4 members, 14 tasks, Kabir's blocker,
    an open contradiction, commits, and verified risks.
    Idempotent: drops and repopulates DEMO01 data.
    """
    if not force and target_session is None:
        confirm = input("This will reset and seed demo data for DEMO01. Proceed? (y/N): ")
        if confirm.strip().lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Use provided session or open a new one
    sess = target_session if target_session is not None else Session(engine)

    try:
        # Clean existing DEMO01 project if present
        existing_proj = sess.exec(select(Project).where(Project.code == "DEMO01")).first()
        if existing_proj:
            pid = existing_proj.id
            # Delete dependent rows
            tasks = sess.exec(select(Task).where(Task.project_id == pid)).all()
            t_ids = [t.id for t in tasks]

            sess.exec(select(TaskDep)).all()
            for d in sess.exec(select(TaskDep).where(TaskDep.task_id.in_(t_ids))).all():
                sess.delete(d)
            for v in sess.exec(select(Verification).where(Verification.task_id.in_(t_ids))).all():
                sess.delete(v)
            for b in sess.exec(select(Blocker).where(Blocker.task_id.in_(t_ids))).all():
                sess.delete(b)
            for t in tasks:
                sess.delete(t)
            for blk in sess.exec(select(Block).where(Block.project_id == pid)).all():
                sess.delete(blk)
            for m in sess.exec(select(Member).where(Member.project_id == pid)).all():
                sess.delete(m)
            for c in sess.exec(select(CommitLog).where(CommitLog.project_id == pid)).all():
                sess.delete(c)
            for con in sess.exec(select(Contradiction).where(Contradiction.project_id == pid)).all():
                sess.delete(con)
            for e in sess.exec(select(Event).where(Event.project_id == pid)).all():
                sess.delete(e)
            for msg in sess.exec(select(Message).where(Message.project_id == pid)).all():
                sess.delete(msg)

            sess.delete(existing_proj)
            sess.flush()

        now = datetime.now(timezone.utc)
        starts_at = now - timedelta(hours=4)
        ends_at = now + timedelta(hours=16)

        # 1. Project
        project = Project(
            code="DEMO01",
            name="Pilot: Autonomous AI Project Coordinator",
            idea="An AI bot that coordinates student hackathon teams, checks git evidence, and routes blockers.",
            repo_url="https://github.com/pilot-team/pilot",
            status="running",
            starts_at=starts_at,
            ends_at=ends_at,
        )
        sess.add(project)
        sess.flush()
        pid = project.id

        # 2. Members (4 members)
        m_meera = Member(
            project_id=pid,
            name="Meera",
            role="lead",
            github_login="meera-lead",
            skills="python fastapi postgresql architecture management",
            invite_status="accepted",
        )
        m_kabir = Member(
            project_id=pid,
            name="Kabir",
            role="member",
            github_login="kabir-dev",
            skills="external-apis payments stripe backend integration",
            invite_status="accepted",
        )
        m_aarav = Member(
            project_id=pid,
            name="Aarav",
            role="member",
            github_login="aarav-bot",
            skills="telegram async-python loops scheduling devops",
            invite_status="accepted",
        )
        m_diya = Member(
            project_id=pid,
            name="Diya",
            role="member",
            github_login="diya-qa",
            skills="git testing verification diff-inspection metrics",
            invite_status="accepted",
        )
        sess.add_all([m_meera, m_kabir, m_aarav, m_diya])
        sess.flush()

        project.lead_member_id = m_meera.id
        sess.add(project)

        # 3. Blocks (at least 1 oversize block)
        b1 = Block(project_id=pid, name="Core & Database Spine", owner_member_id=m_meera.id, total_effort=12, oversize_flag=False)
        b2 = Block(project_id=pid, name="Backend Integrations & Brain", owner_member_id=m_kabir.id, total_effort=18, oversize_flag=True)
        b3 = Block(project_id=pid, name="Telegram Bot & Check-in Loop", owner_member_id=m_aarav.id, total_effort=10, oversize_flag=False)
        b4 = Block(project_id=pid, name="GitHub Verification & Stats", owner_member_id=m_diya.id, total_effort=8, oversize_flag=False)
        sess.add_all([b1, b2, b3, b4])
        sess.flush()

        # 4. Tasks (14 tasks across statuses)
        # 3 verified_done, 3 in_progress, 1 claimed_done, 1 needs_review, 1 blocked, 5 todo (including 1 milestone)
        tasks_data = [
            # Verified done (Block 1)
            {"key": "T-1", "title": "Repo Setup & Project Skeleton", "effort": 3, "status": "verified_done", "block_id": b1.id, "owner": m_meera.id, "progress": 100, "risk": "ok", "ms": False, "comp": now - timedelta(hours=3)},
            {"key": "T-2", "title": "Database Schema & Models", "effort": 4, "status": "verified_done", "block_id": b1.id, "owner": m_meera.id, "progress": 100, "risk": "ok", "ms": False, "comp": now - timedelta(hours=2)},
            {"key": "T-3", "title": "FastAPI Base Routes & Health Check", "effort": 5, "status": "verified_done", "block_id": b1.id, "owner": m_meera.id, "progress": 100, "risk": "ok", "ms": False, "comp": now - timedelta(hours=1)},
            # In progress (Block 3 & 4)
            {"key": "T-4", "title": "Telegram Bot Initialization & Webhook", "effort": 5, "status": "in_progress", "block_id": b3.id, "owner": m_aarav.id, "progress": 60, "risk": "ok", "ms": False},
            {"key": "T-5", "title": "Check-in Scheduler & Delivery Loop", "effort": 5, "status": "in_progress", "block_id": b3.id, "owner": m_aarav.id, "progress": 40, "risk": "ok", "ms": False},
            {"key": "T-6", "title": "GitHub Commit Poller & Ingestion", "effort": 4, "status": "in_progress", "block_id": b4.id, "owner": m_diya.id, "progress": 50, "risk": "ok", "ms": False},
            # Blocked (Block 2 - Kabir)
            {"key": "T-7", "title": "Payment & API Integration", "effort": 6, "status": "blocked", "block_id": b2.id, "owner": m_kabir.id, "progress": 30, "risk": "at_risk", "ms": False},
            # Claimed done & Needs review
            {"key": "T-8", "title": "Verifier Engine & LLM Diff Inspector", "effort": 4, "status": "claimed_done", "block_id": b4.id, "owner": m_diya.id, "progress": 90, "risk": "ok", "ms": False},
            {"key": "T-9", "title": "Risk Recompute & Slip Detection", "effort": 4, "status": "needs_review", "block_id": b2.id, "owner": m_kabir.id, "progress": 85, "risk": "ok", "ms": False},
            # Todo (Block 1, 2, 3, 4, and Milestone)
            {"key": "T-10", "title": "Contradiction Resolution Logic", "effort": 4, "status": "todo", "block_id": b2.id, "owner": m_kabir.id, "progress": 0, "risk": "at_risk", "ms": False},
            {"key": "T-11", "title": "Guide Agent Proactive Digest", "effort": 4, "status": "todo", "block_id": b1.id, "owner": m_meera.id, "progress": 0, "risk": "ok", "ms": False},
            {"key": "T-12", "title": "Interactive Kanban & DAG Visualization", "effort": 4, "status": "todo", "block_id": b3.id, "owner": m_aarav.id, "progress": 0, "risk": "ok", "ms": False},
            {"key": "T-13", "title": "Contribution Heatmap & Commit Stats", "effort": 4, "status": "todo", "block_id": b4.id, "owner": m_diya.id, "progress": 0, "risk": "ok", "ms": False},
            {"key": "T-14", "title": "Demo & Final Pitch Presentation", "effort": 2, "status": "todo", "block_id": None, "owner": m_meera.id, "progress": 0, "risk": "at_risk", "ms": True},
        ]

        task_records: dict[str, Task] = {}
        for d in tasks_data:
            t = Task(
                project_id=pid,
                key=d["key"],
                title=d["title"],
                description=f"Scope and implementation for {d['title']}",
                effort=d["effort"],
                status=d["status"],
                block_id=d["block_id"],
                owner_member_id=d["owner"],
                progress=d["progress"],
                risk=d["risk"],
                is_milestone=d["ms"],
                acceptance_criteria=[f"Criteria 1 for {d['title']}", f"Criteria 2 for {d['title']}"],
                completed_at=d.get("comp"),
                started_at=starts_at if d["status"] != "todo" else None,
                deadline=now + timedelta(hours=int(d["key"].split("-")[1])),
            )
            sess.add(t)
            task_records[d["key"]] = t
        sess.flush()

        # Dependencies
        deps_data = [
            ("T-3", "T-1"),
            ("T-7", "T-3"),
            ("T-10", "T-7"),
            ("T-14", "T-10"),
        ]
        for child_key, parent_key in deps_data:
            sess.add(TaskDep(task_id=task_records[child_key].id, depends_on_task_id=task_records[parent_key].id, kind="hard"))
        sess.flush()

        # 5. Kabir's Blocker
        blocker = Blocker(
            task_id=task_records["T-7"].id,
            description="connected, but waiting for test credentials",
            type="dependency",
            needed_from="Meera",
            status="open",
            created_at=now - timedelta(hours=8),
        )
        sess.add(blocker)
        sess.flush()

        # 6. Contradiction
        contradiction = Contradiction(
            project_id=pid,
            task_ids=["T-7"],
            member_ids=[m_meera.id, m_kabir.id],
            summary="Meera says the integration is done; Kabir says he is waiting on the API.",
            status="open",
            created_at=now - timedelta(hours=1),
        )
        sess.add(contradiction)
        sess.flush()

        # 7. Verifications
        sess.add(Verification(task_id=task_records["T-1"].id, verdict="verified", confidence=0.95, reason="Repo setup verified"))
        sess.add(Verification(task_id=task_records["T-2"].id, verdict="verified", confidence=0.92, reason="Schema matches"))
        sess.add(Verification(task_id=task_records["T-3"].id, verdict="verified", confidence=0.90, reason="Health endpoints pass"))
        sess.add(Verification(task_id=task_records["T-8"].id, verdict="partial", confidence=0.60, reason="Missing test coverage"))
        sess.add(Verification(task_id=task_records["T-9"].id, verdict="partial", confidence=0.50, reason="Needs review on circular edges"))
        sess.flush()

        # 8. Commits (Spread across members + one with wrong author)
        commits_data = [
            {"sha": "c001a11", "author": "meera-lead", "mid": m_meera.id, "msg": "Init repository and fastapi", "add": 150, "del": 10, "tid": task_records["T-1"].id},
            {"sha": "c002b22", "author": "meera-lead", "mid": m_meera.id, "msg": "Add models and tables", "add": 200, "del": 15, "tid": task_records["T-2"].id},
            {"sha": "c003c33", "author": "kabir-dev", "mid": m_kabir.id, "msg": "Draft payment gateway endpoints", "add": 80, "del": 5, "tid": task_records["T-7"].id},
            {"sha": "c004d44", "author": "aarav-bot", "mid": m_aarav.id, "msg": "Telegram handler skeleton", "add": 120, "del": 8, "tid": task_records["T-4"].id},
            {"sha": "c005e55", "author": "diya-qa", "mid": m_diya.id, "msg": "GitHub poller implementation", "add": 95, "del": 12, "tid": task_records["T-6"].id},
            {"sha": "c006f66", "author": "unknown-ghost", "mid": None, "msg": "Commit with wrong author login", "add": 30, "del": 2, "tid": task_records["T-6"].id},
        ]
        for c in commits_data:
            sess.add(
                CommitLog(
                    sha=c["sha"],
                    project_id=pid,
                    author_login=c["author"],
                    member_id=c["mid"],
                    message=c["msg"],
                    additions=c["add"],
                    deletions=c["del"],
                    committed_at=now - timedelta(hours=2),
                    task_id=c["tid"],
                )
            )
        sess.flush()

        # 9. Events
        add_event(sess, pid, "project_created", actor_member_id=m_meera.id, payload={"code": "DEMO01", "name": project.name})
        add_event(sess, pid, "tasks_bundled", payload={"block_count": 4, "task_count": 14})
        add_event(sess, pid, "blocker_opened", task_id=task_records["T-7"].id, actor_member_id=m_kabir.id, payload={"description": "connected, but waiting for test credentials"})
        add_event(sess, pid, "contradiction_opened", payload={"summary": "Meera says integration is done; Kabir says waiting on API"})

        # Run risk recompute so risks and downstream ripple reflect the seed
        risk_recompute(sess, pid)
        sess.commit()
        print("DEMO01 successfully seeded with 4 members, 14 tasks, blocker, and contradiction.")
        return project

    finally:
        if target_session is None:
            sess.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed DEMO01 backup project into Pilot database.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    seed_database(force=args.force)
