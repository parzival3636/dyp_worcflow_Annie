"""
TaskSink interface and stub for handing approved tasks to Pilot core.
"""
from __future__ import annotations

from typing import Protocol, Optional
from datetime import date
from pydantic import BaseModel


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
