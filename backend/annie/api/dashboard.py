from fastapi import APIRouter
from annie.core.database import get_supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Annie Dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    """Aggregate stats for the dashboard: tasks, team, recent activity."""
    db = get_supabase()

    try:
        tasks_result = db.table("tasks").select("*").execute()
        tasks = tasks_result.data or []
    except Exception as e:
        logger.warning("Error fetching tasks for dashboard stats: %s", e)
        tasks = []

    total = len(tasks)
    complete = sum(1 for t in tasks if t.get("status") == "complete")
    in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
    pending = sum(1 for t in tasks if t.get("status") == "pending")

    # Recent verifications
    try:
        verifications = (
            db.table("verifications")
            .select("*")
            .order("processed_at", desc=True)
            .limit(20)
            .execute()
        )
        verifications_data = verifications.data or []
    except Exception as e:
        logger.warning("Error fetching verifications for dashboard: %s", e)
        verifications_data = []

    # Team stats — group by assignee
    team_stats: dict[str, dict] = {}
    for task in tasks:
        for member in task.get("assigned_to", []) or []:
            if member not in team_stats:
                team_stats[member] = {"total": 0, "complete": 0, "in_progress": 0}
            team_stats[member]["total"] += 1
            if task.get("status") == "complete":
                team_stats[member]["complete"] += 1
            elif task.get("status") == "in_progress":
                team_stats[member]["in_progress"] += 1

    return {
        "task_summary": {
            "total": total,
            "complete": complete,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": round((complete / total * 100) if total else 0, 1),
        },
        "recent_verifications": verifications_data,
        "team_stats": [
            {"username": k, **v} for k, v in team_stats.items()
        ],
    }


@router.get("/webhook-events")
async def get_webhook_events(status: str | None = None, limit: int = 50):
    """List recent webhook events from Supabase."""
    db = get_supabase()
    try:
        query = db.table("webhook_events").select("*").order("created_at", desc=True).limit(limit)
        if status and status != "all":
            query = query.eq("status", status)
        result = query.execute()
        return {"events": result.data or []}
    except Exception as e:
        logger.warning("Error fetching webhook events: %s", e)
        return {"events": []}
