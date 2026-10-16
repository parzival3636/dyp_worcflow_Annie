"""
TaskSink interface and implementations for handing approved tasks to Pilot core.
"""
from __future__ import annotations

import logging
from typing import Protocol, Optional
from datetime import date, datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger("transcribe.tasks_sink")


class TaskPayload(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    owner_member_id: Optional[str] = None
    deadline: Optional[date] = None
    evidence: str
    meeting_id: str


class TaskSink(Protocol):
    def create_task(self, task: TaskPayload) -> str:
        ...


class InMemoryTaskSink:
    def __init__(self):
        self.created_tasks: list[TaskPayload] = []

    def create_task(self, task: TaskPayload) -> str:
        self.created_tasks.append(task)
        return f"task_{len(self.created_tasks)}"


class PilotDbTaskSink:
    """Inserts approved tasks directly into Pilot SQLModel Task table."""

    def create_task(self, task: TaskPayload) -> str:
        try:
            from db import get_session
            from models import Project, Task, Event
            from sqlmodel import select
        except ImportError:
            from backend.db import get_session
            from backend.models import Project, Task, Event
            from sqlmodel import select

        with get_session() as session:
            # Find project by code or id
            project = None
            if str(task.project_id).isdigit():
                project = session.get(Project, int(task.project_id))
            if not project:
                project = session.exec(
                    select(Project).where(Project.code == task.project_id)
                ).first()

            if not project:
                logger.warning("PilotDbTaskSink: Project '%s' not found.", task.project_id)
                return "error_project_not_found"

            existing_tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
            next_num = len(existing_tasks) + 1
            key = f"T-{next_num}"

            owner_id = None
            if task.owner_member_id and str(task.owner_member_id).isdigit():
                owner_id = int(task.owner_member_id)

            deadline_dt = None
            if task.deadline:
                deadline_dt = datetime.combine(task.deadline, datetime.min.time(), tzinfo=timezone.utc)

            new_task = Task(
                project_id=project.id,
                key=key,
                title=task.title,
                description=task.description or f"Extracted from meeting {task.meeting_id}:\n{task.evidence}",
                owner_member_id=owner_id,
                deadline=deadline_dt,
                status="todo",
                risk="ok",
                effort=3,
                progress=0,
            )
            session.add(new_task)
            session.flush()

            session.add(
                Event(
                    project_id=project.id,
                    ts=datetime.now(timezone.utc),
                    actor_member_id=owner_id,
                    type="task_created",
                    task_id=new_task.id,
                    payload={"key": key, "title": task.title, "source": "meeting_transcript", "meeting_id": task.meeting_id},
                )
            )
            session.commit()
            logger.info("Created Pilot task %s (%s) from transcript.", key, task.title)
            return key
