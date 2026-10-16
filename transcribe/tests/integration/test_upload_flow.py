"""
Integration tests for manual transcript upload flow (PRD Section 15.4, U1-U6).
"""
import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.orm import Meeting, MeetingStatusEnum


def test_upload_flow_txt(client: TestClient, db_session: Session):
    content = b"Rahul: Hey team let us organize sprint.\nPriya: I will finish the login page by Friday.\nAnita: I can prepare slides by tomorrow.\nRahul: I will set up database schema by end of month."
    files = {"file": ("sprint.txt", io.BytesIO(content), "text/plain")}
    data = {"project_id": "proj_up1", "title": "Manual Sprint Sync"}

    resp = client.post("/api/v1/transcribe/meetings/upload", data=data, files=files)
    assert resp.status_code == 200
    res_data = resp.json()
    assert "meeting_id" in res_data
    meeting_id = res_data["meeting_id"]

    meeting = db_session.get(Meeting, meeting_id)
    assert meeting is not None
    assert meeting.project_id == "proj_up1"


def test_upload_empty_transcript_sets_status(client: TestClient, db_session: Session):
    content = b"Rahul: Hey."  # less than 20 words
    files = {"file": ("empty.txt", io.BytesIO(content), "text/plain")}
    data = {"project_id": "proj_empty", "title": "Empty Call"}

    resp = client.post("/api/v1/transcribe/meetings/upload", data=data, files=files)
    assert resp.status_code == 200
    meeting_id = resp.json()["meeting_id"]

    meeting = db_session.get(Meeting, meeting_id)
    assert meeting.status == MeetingStatusEnum.TRANSCRIPT_EMPTY
