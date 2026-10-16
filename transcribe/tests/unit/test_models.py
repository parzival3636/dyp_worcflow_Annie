"""
Unit tests for SQLAlchemy ORM models and constraints.
"""
from datetime import datetime, timezone, date
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.orm import (
    Meeting,
    TranscriptSegment,
    RawPayload,
    WebhookEvent,
    ProposedTask,
    PlatformEnum,
    ProviderEnum,
    MeetingStatusEnum,
    ItemTypeEnum,
    ProposedTaskStatusEnum,
)


def test_create_meeting(db_session: Session):
    meeting = Meeting(
        project_id="proj_alpha",
        title="Sprint sync",
        meeting_link="https://meet.google.com/abc-defg-hij",
        platform=PlatformEnum.GOOGLE_MEET,
        provider=ProviderEnum.FIREFLIES,
        status=MeetingStatusEnum.BOT_REQUESTED,
        consent_confirmed=True,
    )
    db_session.add(meeting)
    db_session.commit()

    retrieved = db_session.get(Meeting, meeting.id)
    assert retrieved is not None
    assert retrieved.project_id == "proj_alpha"
    assert retrieved.consent_confirmed is True


def test_transcript_segments_unique_constraint(db_session: Session):
    meeting = Meeting(
        project_id="proj_alpha",
        consent_confirmed=True,
    )
    db_session.add(meeting)
    db_session.commit()

    seg1 = TranscriptSegment(
        meeting_id=meeting.id,
        idx=0,
        speaker_raw="Alice",
        text="Hello team",
        start_s=0.0,
        end_s=2.5,
    )
    db_session.add(seg1)
    db_session.commit()

    # Duplicate (meeting_id, idx) should violate unique constraint
    seg2 = TranscriptSegment(
        meeting_id=meeting.id,
        idx=0,
        speaker_raw="Bob",
        text="Duplicate idx",
        start_s=2.5,
        end_s=4.0,
    )
    db_session.add(seg2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_raw_payload_creation(db_session: Session):
    meeting = Meeting(
        project_id="proj_beta",
        consent_confirmed=True,
    )
    db_session.add(meeting)
    db_session.commit()

    payload = RawPayload(
        meeting_id=meeting.id,
        provider="FIREFLIES",
        payload_json={"sample": "data"},
    )
    db_session.add(payload)
    db_session.commit()

    assert payload.id is not None
    assert payload.payload_json["sample"] == "data"


def test_webhook_event_idempotency_constraint(db_session: Session):
    evt1 = WebhookEvent(
        provider="FIREFLIES",
        provider_meeting_id="ff_meet_123",
        event_type="Transcription completed",
    )
    db_session.add(evt1)
    db_session.commit()

    # Duplicate (provider, provider_meeting_id, event_type)
    evt2 = WebhookEvent(
        provider="FIREFLIES",
        provider_meeting_id="ff_meet_123",
        event_type="Transcription completed",
    )
    db_session.add(evt2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_proposed_task_fingerprint_unique_per_meeting(db_session: Session):
    meeting = Meeting(
        project_id="proj_gamma",
        consent_confirmed=True,
    )
    db_session.add(meeting)
    db_session.commit()

    task1 = ProposedTask(
        meeting_id=meeting.id,
        type=ItemTypeEnum.TASK,
        title="Setup Auth",
        confidence=0.95,
        evidence="I will set up auth",
        fingerprint="fingerprint_auth_1",
        ambiguity_flags=["NO_DEADLINE"],
    )
    db_session.add(task1)
    db_session.commit()

    # Same meeting and same fingerprint must fail
    task2 = ProposedTask(
        meeting_id=meeting.id,
        type=ItemTypeEnum.TASK,
        title="Setup Auth Duplicate",
        confidence=0.95,
        evidence="I will set up auth duplicate",
        fingerprint="fingerprint_auth_1",
    )
    db_session.add(task2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
