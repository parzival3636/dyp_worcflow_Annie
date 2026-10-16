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
    logger.info("[stub] generate_tasks for project %d", project_id)
    return []


def bundle_and_assign(project_id: int) -> dict:
    logger.info("[stub] bundle_and_assign for project %d", project_id)
    return {"blocks": []}


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
