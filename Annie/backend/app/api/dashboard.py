from fastapi import APIRouter
from app.core.database import get_supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    """Aggregate stats for the dashboard: tasks, team, recent activity."""
    db = get_supabase()

    tasks_result = db.table("tasks").select("*").execute()
    tasks = tasks_result.data or []

    total = len(tasks)
    complete = sum(1 for t in tasks if t["status"] == "complete")
    in_progress = sum(1 for t in tasks if t["status"] == "in_progress")
    pending = sum(1 for t in tasks if t["status"] == "pending")

    # Recent verifications
    verifications = (
        db.table("verifications")
        .select("*")
        .order("processed_at", desc=True)
        .limit(20)
        .execute()
    )

    # Team stats — group by assignee
    team_stats: dict[str, dict] = {}
    for task in tasks:
        for member in task.get("assigned_to", []):
            if member not in team_stats:
                team_stats[member] = {"total": 0, "complete": 0, "in_progress": 0}
            team_stats[member]["total"] += 1
            if task["status"] == "complete":
                team_stats[member]["complete"] += 1
            elif task["status"] == "in_progress":
                team_stats[member]["in_progress"] += 1

    return {
        "task_summary": {
            "total": total,
            "complete": complete,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": round((complete / total * 100) if total else 0, 1),
        },
        "recent_verifications": verifications.data,
        "team_stats": [
            {"username": k, **v} for k, v in team_stats.items()
        ],
    }


@router.get("/webhook-events")
async def get_webhook_events(status: str | None = None, limit: int = 50):
    """List recent webhook events from Supabase."""
    db = get_supabase()
    query = db.table("webhook_events").select("*").order("created_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return {"events": result.data}
