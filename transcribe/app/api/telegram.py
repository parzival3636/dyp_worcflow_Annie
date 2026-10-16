"""
Telegram webhook callback and interactive button handler.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.config import get_settings
from app.integrations.tasks import PilotDbTaskSink, TaskPayload, TaskSink
from app.models.orm import (
    Meeting,
    MeetingStatusEnum,
    ProposedTask,
    ProposedTaskStatusEnum,
)
from app.services.notifier import TelegramNotifier

router = APIRouter()
logger = logging.getLogger("transcribe.telegram_api")

# Shared task sink instance for application runtime
_task_sink: TaskSink = PilotDbTaskSink()


def get_task_sink() -> TaskSink:
    return _task_sink


def set_task_sink(sink: TaskSink):
    global _task_sink
    _task_sink = sink


@router.post("/telegram/callback")
async def telegram_webhook_callback(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    session: Session = Depends(get_session),
):
    settings = get_settings()

    # Verify secret token
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram secret token.")

    try:
        body = await request.json()
    except Exception:
        return Response(status_code=200)

    # 1. Handle Callback Queries (Approve / Edit / Reject buttons)
    if "callback_query" in body:
        cq = body["callback_query"]
        cq_data = cq.get("data", "")
        chat_id = str(cq.get("message", {}).get("chat", {}).get("id", ""))

        if cq_data.startswith("tr:"):
            parts = cq_data.split(":")
            if len(parts) >= 3:
                action = parts[1]
                task_id = parts[2]

                task = session.get(ProposedTask, task_id)
                if not task:
                    # Gracefully acknowledge missing task
                    return Response(status_code=200, content="Task not found")

                task_sink = get_task_sink()

                if action == "approve":
                    # Guard against double tap
                    if task.status != ProposedTaskStatusEnum.APPROVED:
                        task.status = ProposedTaskStatusEnum.APPROVED
                        session.add(task)
                        session.commit()

                        meeting = session.get(Meeting, task.meeting_id)
                        # Hand off to Pilot Task Sink
                        task_sink.create_task(
                            TaskPayload(
                                project_id=meeting.project_id if meeting else "unknown",
                                title=task.title,
                                description=task.description,
                                owner_member_id=task.owner_member_id,
                                deadline=task.deadline_iso,
                                evidence=task.evidence,
                                meeting_id=task.meeting_id,
                            )
                        )

                elif action == "reject":
                    task.status = ProposedTaskStatusEnum.REJECTED
                    session.add(task)
                    session.commit()

                # Check if all tasks for the meeting are now resolved
                remaining_unresolved = (
                    session.query(ProposedTask)
                    .filter(
                        ProposedTask.meeting_id == task.meeting_id,
                        ProposedTask.status.in_([
                            ProposedTaskStatusEnum.PENDING,
                            ProposedTaskStatusEnum.NEEDS_CLARIFICATION,
                        ]),
                    )
                    .count()
                )

                if remaining_unresolved == 0:
                    meeting = session.get(Meeting, task.meeting_id)
                    if meeting and meeting.status != MeetingStatusEnum.COMPLETED:
                        meeting.status = MeetingStatusEnum.COMPLETED
                        session.add(meeting)
                        session.commit()

        return Response(status_code=200, content="OK")

    return Response(status_code=200, content="OK")
