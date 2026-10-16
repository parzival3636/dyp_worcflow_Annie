"""
Integration tests for POST /meetings API (PRD Section 15.2, M1-M9).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.orm import Meeting, MeetingStatusEnum
from app.services.meeting_service import transition


def test_m1_valid_link_consent_true(client: TestClient):
    payload = {
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "project_id": "proj_m1",
        "title": "Planning",
        "consent_confirmed": True,
    }
    resp = client.post("/api/v1/transcribe/meetings", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "BOT_REQUESTED"
    assert "meeting_id" in data


def test_m2_consent_false_rejected(client: TestClient):
    payload = {
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "project_id": "proj_m2",
        "consent_confirmed": False,
    }
    resp = client.post("/api/v1/transcribe/meetings", json=payload)
    assert resp.status_code == 422


def test_m3_missing_project_id_rejected(client: TestClient):
    payload = {
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "consent_confirmed": True,
    }
    resp = client.post("/api/v1/transcribe/meetings", json=payload)
    assert resp.status_code == 422


def test_m4_duplicate_link_returns_200(client: TestClient):
    payload = {
        "meeting_link": "https://meet.google.com/xyz-uvwx-rst",
        "project_id": "proj_m4",
        "consent_confirmed": True,
    }
    r1 = client.post("/api/v1/transcribe/meetings", json=payload)
    assert r1.status_code == 201
    m1_id = r1.json()["meeting_id"]

    r2 = client.post("/api/v1/transcribe/meetings", json=payload)
    assert r2.status_code == 200
    assert r2.json()["meeting_id"] == m1_id


def test_m8_rate_limiting_6th_request(client: TestClient):
    project_id = "proj_rate_test"
    payload = {
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "project_id": project_id,
        "consent_confirmed": True,
    }
    # 5 requests pass (first is 201, next 4 are 200 duplicates)
    for _ in range(5):
        resp = client.post("/api/v1/transcribe/meetings", json=payload)
        assert resp.status_code in (200, 201)

    # 6th request triggers 429
    r6 = client.post("/api/v1/transcribe/meetings", json=payload)
    assert r6.status_code == 429


def test_m9_illegal_transition():
    meeting = Meeting(status=MeetingStatusEnum.COMPLETED, project_id="p1")
    with pytest.raises(ValueError, match="Illegal meeting status transition"):
        transition(meeting, MeetingStatusEnum.BOT_REQUESTED)
