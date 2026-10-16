"""
Pilot – stub implementations for teammate modules.

Each function returns plausible fake data and logs a line.
Teammates will swap the bodies without changing signatures.
"""
from __future__ import annotations

import logging
from config import get_settings

logger = logging.getLogger("pilot.stubs")


def parse_idea(idea: str) -> dict:
    """Return parsed idea dict: {name, summary, duration_hours}."""
    logger.info("[stub] parse_idea called with: %s", idea[:80])
    words = idea.strip().split()
    name = "-".join(words[:4]).lower() if words else "project"
    return {"name": name, "summary": idea, "duration_hours": 48}


def create_repo(name: str) -> dict:
    """Return {full_name, url} or raise."""
    logger.info("[stub] create_repo called for: %s", name)
    return {
        "full_name": f"pilot-team/{name}",
        "url": f"https://github.com/pilot-team/{name}",
    }


def validate_github_user(login: str) -> bool:
    logger.info("[stub] validate_github_user: %s", login)
    return True


def invite_collaborator(repo: str, login: str) -> None:
    logger.info("[stub] invite_collaborator: %s -> %s", login, repo)


def generate_tasks(project_id: int) -> list[int]:
    """Generate initial task breakdown for project."""
    logger.info("generate_tasks for project %d", project_id)
    from datetime import datetime, timezone, timedelta
    from sqlmodel import select
    from db import get_session
    from models import Project, Task

    with get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            return []

        # Check if tasks already exist
        existing = session.exec(select(Task).where(Task.project_id == project_id)).all()
        if existing:
            return [t.id for t in existing if t.id is not None]

        idea_lower = (project.idea or project.name or "").lower()
        now = datetime.now(timezone.utc)

        task_defs = [
            ("T-1", "Setup database schema and models", "Design and apply tables, migrations, and database connection pool.", ["PostgreSQL tables created", "ORM models working"], 2, 12),
            ("T-2", "User authentication & JWT API", "Implement signup, login, password hashing and JWT token auth.", ["Register endpoint working", "JWT validated in middleware"], 3, 24),
            ("T-3", "Core CRUD API & business logic", "Implement core endpoints, validation, and database queries.", ["CRUD endpoints working", "Request validation in place"], 4, 36),
            ("T-4", "Frontend UI and component layout", "Build responsive modern pages and connect to backend APIs.", ["Responsive design", "API integration complete"], 4, 40),
            ("T-5", "Testing, bugfixes & deployment", "Run end-to-end testing, resolve blockers, and deploy service.", ["All tests passing", "Service accessible online"], 2, 48),
        ]

        created_ids = []
        for key, title, desc, crit, eff, hours in task_defs:
            task = Task(
                project_id=project_id,
                key=key,
                title=title,
                description=desc,
                acceptance_criteria=crit,
                effort=eff,
                status="todo",
                progress=0,
                deadline=now + timedelta(hours=hours),
            )
            session.add(task)
            session.flush()
            if task.id is not None:
                created_ids.append(task.id)

        session.commit()
        return created_ids


def bundle_and_assign(project_id: int) -> dict:
    """Distribute and assign tasks across project members."""
    logger.info("bundle_and_assign for project %d", project_id)
    from sqlmodel import select
    from db import get_session
    from models import Member, Task

    with get_session() as session:
        members = session.exec(select(Member).where(Member.project_id == project_id)).all()
        tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()

        if not members or not tasks:
            return {"assigned": 0}

        # Round-robin assign tasks to members
        for i, task in enumerate(tasks):
            assigned_member = members[i % len(members)]
            task.owner_member_id = assigned_member.id
            session.add(task)

        session.commit()
        return {"assigned": len(tasks)}


def kickoff(project_id: int) -> None:
    logger.info("[stub] kickoff for project %d", project_id)


def verify_task(task_id: int) -> dict:
    settings = get_settings()
    logger.info("[stub] verify_task for task %d (mode=%s)", task_id, settings.verify_mode)
    if settings.verify_mode == "strict":
        return {"verdict": "needs_review", "confidence": 0.0, "reason": "No evidence found (stub)"}
    return {"verdict": "no_evidence", "confidence": 0.0, "reason": "No evidence found (stub, soft mode)"}


def route_blocker(blocker_id: int) -> None:
    logger.info("[stub] route_blocker for blocker %d", blocker_id)


def check_contradictions(project_id: int, trigger_task_id: int | None) -> None:
    logger.info("[stub] check_contradictions project=%d task=%s", project_id, trigger_task_id)


def recompute_ripple(project_id: int) -> None:
    logger.info("[stub] recompute_ripple for project %d", project_id)


def guide_answer(project_id: int, question: str) -> str:
    logger.info("[stub] guide_answer project=%d q=%s", project_id, question[:60])
    return "I don't have enough context to answer that yet — the Guide module isn't connected."


def guide_report(project_id: int) -> str:
    logger.info("[stub] guide_report for project %d", project_id)
    return "📊 *Project Report (stub)*\nNo data available yet."


def escalate_to_lead(member_id: int, task_id: int) -> None:
    logger.info("[stub] escalate_to_lead member=%d task=%d", member_id, task_id)
