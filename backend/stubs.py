"""
Pilot – integrations for planner, guide, ripple, contradiction, routing modules.
"""
from __future__ import annotations

import json
import logging
from config import get_settings

logger = logging.getLogger("pilot.stubs")


def parse_idea(idea: str) -> dict:
    """Return parsed idea dict: {name, summary, duration_hours}."""
    logger.info("parse_idea called with: %s", idea[:80])
    words = idea.strip().split()
    name = "-".join(words[:4]).lower() if words else "project"
    return {"name": name, "summary": idea, "duration_hours": 48}


def create_repo(name: str) -> dict:
    """Create GitHub repo via GitHubService if token is available, or return fallback."""
    settings = get_settings()
    logger.info("create_repo called for: %s", name)
    if settings.github_token:
        try:
            from annie.services.github_service import GitHubService
            gh = GitHubService()
            return gh.create_repo(name=name, description=f"Pilot managed project: {name}", private=False)
        except Exception as exc:
            logger.warning("GitHub create_repo failed, using local format: %s", exc)

    owner = settings.github_owner or settings.github_username or "pilot-team"
    return {
        "full_name": f"{owner}/{name}",
        "url": f"https://github.com/{owner}/{name}",
    }


def validate_github_user(login: str) -> bool:
    logger.info("validate_github_user: %s", login)
    settings = get_settings()
    if settings.github_token:
        try:
            import httpx
            resp = httpx.get(
                f"https://api.github.com/users/{login}",
                headers={"Authorization": f"Bearer {settings.github_token}"},
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return True
    return True


def invite_collaborator(repo: str, login: str) -> None:
    logger.info("invite_collaborator: %s -> %s", login, repo)
    settings = get_settings()
    if settings.github_token and repo and login:
        try:
            from annie.services.github_service import GitHubService
            gh = GitHubService()
            gh.invite_collaborator(repo, login)
        except Exception as exc:
            logger.warning("GitHub invite_collaborator error: %s", exc)


def generate_tasks(project_id: int) -> list[int]:
    """Generate initial task breakdown for project."""
    logger.info("generate_tasks for project %d", project_id)
    from planner import generate_plan
    from db import get_session
    with get_session() as session:
        try:
            tasks = generate_plan(session, project_id)
            return [t.id for t in tasks if t.id]
        except Exception:
            logger.exception("Failed to generate plan for project %d", project_id)
            return []


def bundle_and_assign(project_id: int) -> dict:
    """Bundle tasks and assign them to team members."""
    logger.info("bundle_and_assign for project %d", project_id)
    from planner import bundle, assign
    from db import get_session
    with get_session() as session:
        try:
            bundle(session, project_id)
            return assign(session, project_id)
        except Exception:
            logger.exception("Failed to bundle and assign for project %d", project_id)
            return {"assigned": 0}


def kickoff(project_id: int) -> None:
    logger.info("kickoff for project %d", project_id)
    from db import get_session
    from models import Project, Event
    from datetime import datetime, timezone
    with get_session() as session:
        project = session.get(Project, project_id)
        if project:
            project.status = "running"
            project.starts_at = datetime.now(timezone.utc)
            session.add(project)
            session.add(
                Event(
                    project_id=project_id,
                    ts=datetime.now(timezone.utc),
                    type="status_changed",
                    payload={"from": "planning", "to": "running", "reason": "Kickoff"},
                )
            )


def verify_task(task_id: int) -> dict:
    logger.info("verify_task executing for task %d", task_id)
    try:
        from verify import verify_task_sync
        return verify_task_sync(task_id)
    except Exception as exc:
        logger.exception("Verification pipeline error for task %d: %s", task_id, exc)
        return {"verdict": "no_evidence", "confidence": 0.0, "reason": str(exc), "matched_shas": []}


def route_blocker(blocker_id: int) -> None:
    logger.info("route_blocker for blocker %d", blocker_id)
    from routing import route_blocker as do_route
    from db import get_session
    with get_session() as session:
        try:
            do_route(session, blocker_id)
        except Exception:
            logger.exception("Failed to route blocker %d", blocker_id)


def check_contradictions(project_id: int, trigger_task_id: int | None = None) -> None:
    logger.info("check_contradictions project=%d task=%s", project_id, trigger_task_id)
    from contradiction import check_contradictions as do_check
    from db import get_session
    with get_session() as session:
        try:
            do_check(session, project_id)
        except Exception:
            logger.exception("Failed to check contradictions for project %d", project_id)


def recompute_ripple(project_id: int) -> None:
    logger.info("recompute_ripple for project %d", project_id)
    from ripple import risk_recompute
    from db import get_session
    with get_session() as session:
        try:
            risk_recompute(session, project_id)
        except Exception:
            logger.exception("Failed to recompute ripple for project %d", project_id)


def guide_answer(project_id: int, question: str) -> str:
    logger.info("guide_answer project=%d q=%s", project_id, question[:60])
    from guide import run_guide_query
    from db import get_session
    with get_session() as session:
        try:
            res = run_guide_query(session, project_id, question)
            return res.get("answer", "")
        except Exception:
            return "Guide unavailable."


def guide_report(project_id: int) -> str:
    logger.info("guide_report for project %d", project_id)
    from guide import generate_report
    from db import get_session
    with get_session() as session:
        try:
            rep = generate_report(session, project_id)
            return json.dumps(rep, indent=2)
        except Exception:
            return "Report generation failed."


def escalate_to_lead(member_id: int, task_id: int) -> None:
    logger.info("escalate_to_lead member=%d task=%d", member_id, task_id)
