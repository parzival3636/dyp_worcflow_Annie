from fastapi import APIRouter, HTTPException
from app.models.schemas import TaskCreate, TaskResponse
from app.core.database import get_supabase
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse)
async def create_task(payload: TaskCreate):
    """Create a new task linked to a repo."""
    db = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())

    task_data = {
        "id": task_id,
        "title": payload.title,
        "description": payload.description,
        "keywords": payload.keywords,
        "repo_name": payload.repo_name,
        "assigned_to": payload.assigned_to,
        "status": "pending",
        "confidence_score": None,
        "created_at": now,
        "updated_at": now,
    }

    result = db.table("tasks").insert(task_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create task")

    logger.info("Task created: %s - %s", task_id, payload.title)
    return TaskResponse(**result.data[0])


@router.get("/")
async def list_tasks(repo_name: str | None = None, status: str | None = None):
    """List all tasks, optionally filtered by repo or status."""
    db = get_supabase()
    query = db.table("tasks").select("*").order("created_at", desc=True)
    if repo_name:
        query = query.eq("repo_name", repo_name)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return {"tasks": result.data}


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get a single task with its verification history."""
    db = get_supabase()
    task = db.table("tasks").select("*").eq("id", task_id).single().execute()
    if not task.data:
        raise HTTPException(status_code=404, detail="Task not found")

    verifications = (
        db.table("verifications")
        .select("*")
        .eq("task_id", task_id)
        .order("processed_at", desc=True)
        .execute()
    )

    return {"task": task.data, "verifications": verifications.data}


@router.patch("/{task_id}/status")
async def update_task_status(task_id: str, status: str):
    """Manually update a task status."""
    allowed = {"pending", "in_progress", "complete"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")

    db = get_supabase()
    result = (
        db.table("tasks")
        .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", task_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"updated": result.data[0]}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    db = get_supabase()
    db.table("tasks").delete().eq("id", task_id).execute()
    return {"deleted": task_id}
