"""
Integration tests for Fireflies Webhook endpoint (PRD Section 15.4, W1-W8).
"""
import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.orm import Meeting, MeetingStatusEnum, WebhookEvent

SECRET = "test_webhook_secret"


@pytest.fixture(autouse=True)
def configure_test_secret():
    settings = get_settings()
    old_secret = settings.FIREFLIES_WEBHOOK_SECRET
    settings.FIREFLIES_WEBHOOK_SECRET = SECRET
    yield
    settings.FIREFLIES_WEBHOOK_SECRET = old_secret


def _sign(body: bytes, secret: str = SECRET) -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def test_w1_valid_webhook_flow(client: TestClient, db_session: Session):
    meeting = Meeting(
        project_id="proj_w1",
        provider_meeting_id="ff_meet_w1",
        status=MeetingStatusEnum.BOT_REQUESTED,
        consent_confirmed=True,
    )
    db_session.add(meeting)
    db_session.commit()

    payload = {
        "meetingId": "ff_meet_w1",
        "eventType": "Transcription completed",
        "clientReferenceId": None,
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig_header = _sign(raw_body)

    resp = client.post(
        "/api/v1/transcribe/webhooks/fireflies",
        content=raw_body,
        headers={"x-hub-signature": sig_header, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    # Assert webhook_event row created
    evt = db_session.query(WebhookEvent).filter(WebhookEvent.provider_meeting_id == "ff_meet_w1").first()
    assert evt is not None


def test_w2_wrong_signature_401(client: TestClient):
    payload = {"meetingId": "123", "eventType": "Transcription completed"}
    raw_body = json.dumps(payload).encode()
    resp = client.post(
        "/api/v1/transcribe/webhooks/fireflies",
        content=raw_body,
        headers={"x-hub-signature": "sha256=invalidsignature"},
    )
    assert resp.status_code == 401


def test_w3_missing_signature_401(client: TestClient):
    payload = {"meetingId": "123", "eventType": "Transcription completed"}
    resp = client.post("/api/v1/transcribe/webhooks/fireflies", json=payload)
    assert resp.status_code == 401


def test_w4_duplicate_payload_ignored(client: TestClient, db_session: Session):
    payload = {"meetingId": "ff_meet_dup", "eventType": "Transcription completed"}
    raw_body = json.dumps(payload).encode()
    sig = _sign(raw_body)

    # First attempt
    r1 = client.post(
        "/api/v1/transcribe/webhooks/fireflies",
        content=raw_body,
        headers={"x-hub-signature": sig, "Content-Type": "application/json"},
    )
    assert r1.status_code == 200

    # Second attempt (duplicate)
    r2 = client.post(
        "/api/v1/transcribe/webhooks/fireflies",
        content=raw_body,
        headers={"x-hub-signature": sig, "Content-Type": "application/json"},
    )
    assert r2.status_code == 200
    assert "Duplicate" in r2.text


def test_w5_ignored_event_type(client: TestClient):
    payload = {"meetingId": "123", "eventType": "User joined"}
    raw_body = json.dumps(payload).encode()
    sig = _sign(raw_body)

    resp = client.post(
        "/api/v1/transcribe/webhooks/fireflies",
        content=raw_body,
        headers={"x-hub-signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert "ignored" in resp.text.lower()


def test_w7_malformed_json_400(client: TestClient):
    raw_body = b"not-a-json-string"
    sig = _sign(raw_body)

    resp = client.post(
        "/api/v1/transcribe/webhooks/fireflies",
        content=raw_body,
        headers={"x-hub-signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400
