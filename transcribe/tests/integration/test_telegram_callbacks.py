"""
Integration tests for Telegram callbacks and task approvals (PRD Section 15.7, T5-T9).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.api.telegram import get_task_sink, set_task_sink
from app.config import get_settings
from app.integrations.tasks import InMemoryTaskSink
from app.models.orm import (
    Meeting,
    MeetingStatusEnum,
    ProposedTask,
    ProposedTaskStatusEnum,
)


def test_t5_t6_approve_tap_and_double_tap_guard(client: TestClient, db_session: Session):
    task_sink = InMemoryTaskSink()
    set_task_sink(task_sink)

    meeting = Meeting(project_id="proj_tg", status=MeetingStatusEnum.AWAITING_REVIEW, consent_confirmed=True)
    db_session.add(meeting)
    db_session.commit()

    task = ProposedTask(
        meeting_id=meeting.id,
        title="Setup Auth",
        confidence=0.9,
        evidence="I will set up auth",
        fingerprint="fp1",
        status=ProposedTaskStatusEnum.PENDING,
    )
    db_session.add(task)
    db_session.commit()

    body = {
        "callback_query": {
            "id": "cq1",
            "data": f"tr:approve:{task.id}",
            "message": {"chat": {"id": 12345}},
        }
    }

    # First approve tap
    resp1 = client.post("/api/v1/transcribe/telegram/callback", json=body)
    assert resp1.status_code == 200
    assert len(task_sink.created_tasks) == 1

    db_session.refresh(task)
    assert task.status == ProposedTaskStatusEnum.APPROVED

    # Second tap (double tap guard)
    resp2 = client.post("/api/v1/transcribe/telegram/callback", json=body)
    assert resp2.status_code == 200
    assert len(task_sink.created_tasks) == 1  # Still 1!


def test_t7_reject_tap(client: TestClient, db_session: Session):
    meeting = Meeting(project_id="proj_tg2", consent_confirmed=True)
    db_session.add(meeting)
    db_session.commit()

    task = ProposedTask(
        meeting_id=meeting.id,
        title="Optional Task",
        confidence=0.6,
        evidence="Maybe we should do this",
        fingerprint="fp2",
        status=ProposedTaskStatusEnum.PENDING,
    )
    db_session.add(task)
    db_session.commit()

    body = {
        "callback_query": {
            "id": "cq2",
            "data": f"tr:reject:{task.id}",
            "message": {"chat": {"id": 12345}},
        }
    }
    resp = client.post("/api/v1/transcribe/telegram/callback", json=body)
    assert resp.status_code == 200

    db_session.refresh(task)
    assert task.status == ProposedTaskStatusEnum.REJECTED


def test_t8_wrong_secret_token_401(client: TestClient):
    settings = get_settings()
    settings.TELEGRAM_WEBHOOK_SECRET = "real_secret"
    try:
        resp = client.post(
            "/api/v1/transcribe/telegram/callback",
            json={"callback_query": {}},
            headers={"x-telegram-bot-api-secret-token": "wrong_secret"},
        )
        assert resp.status_code == 401
    finally:
        settings.TELEGRAM_WEBHOOK_SECRET = ""


def test_t9_nonexistent_task_id(client: TestClient):
    body = {
        "callback_query": {
            "id": "cq3",
            "data": "tr:approve:nonexistent_uuid",
            "message": {"chat": {"id": 12345}},
        }
    }
    resp = client.post("/api/v1/transcribe/telegram/callback", json=body)
    assert resp.status_code == 200
