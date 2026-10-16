"""
SQLAlchemy ORM models for the transcribe module.
Follows PRD Section 7 exactly with UUID string PKs and required unique constraints.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, date, timezone
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db import Base


def _gen_uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PlatformEnum(str, enum.Enum):
    GOOGLE_MEET = "GOOGLE_MEET"
    ZOOM = "ZOOM"
    TEAMS = "TEAMS"
    UPLOAD = "UPLOAD"
    UNKNOWN = "UNKNOWN"


class ProviderEnum(str, enum.Enum):
    FIREFLIES = "FIREFLIES"
    READAI = "READAI"
    UPLOAD = "UPLOAD"


class MeetingStatusEnum(str, enum.Enum):
    BOT_REQUESTED = "BOT_REQUESTED"
    IN_PROGRESS = "IN_PROGRESS"
    TRANSCRIPT_RECEIVED = "TRANSCRIPT_RECEIVED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    COMPLETED = "COMPLETED"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    TRANSCRIPT_EMPTY = "TRANSCRIPT_EMPTY"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    EXPIRED = "EXPIRED"


class ItemTypeEnum(str, enum.Enum):
    TASK = "task"
    DECISION = "decision"
    BLOCKER = "blocker"
    QUESTION = "question"


class ProposedTaskStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOW_CONFIDENCE_HIDDEN = "LOW_CONFIDENCE_HIDDEN"


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    project_id = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    meeting_link = Column(Text, nullable=True)
    platform = Column(Enum(PlatformEnum), default=PlatformEnum.UNKNOWN, nullable=False)
    provider = Column(Enum(ProviderEnum), default=ProviderEnum.FIREFLIES, nullable=False)
    provider_meeting_id = Column(String(150), nullable=True, unique=True)
    client_reference_id = Column(String(36), default=_gen_uuid, nullable=False)
    status = Column(Enum(MeetingStatusEnum), default=MeetingStatusEnum.BOT_REQUESTED, nullable=False)
    organizer_telegram_id = Column(String(100), nullable=True)
    consent_confirmed = Column(Boolean, default=False, nullable=False)
    unlinked = Column(Boolean, default=False, nullable=False)
    meeting_date = Column(DateTime, nullable=True)
    duration_s = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan")
    raw_payloads = relationship("RawPayload", back_populates="meeting", cascade="all, delete-orphan")
    proposed_tasks = relationship("ProposedTask", back_populates="meeting", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("meeting_id", "idx", name="uq_transcript_segments_meeting_idx"),
    )

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    idx = Column(Integer, nullable=False)
    speaker_raw = Column(String(150), nullable=False)
    member_id = Column(String(100), nullable=True)
    text = Column(Text, nullable=False)
    start_s = Column(Float, nullable=False, default=0.0)
    end_s = Column(Float, nullable=False, default=0.0)

    meeting = relationship("Meeting", back_populates="segments")


class RawPayload(Base):
    __tablename__ = "raw_payloads"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    payload_json = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, default=_now, nullable=False)

    meeting = relationship("Meeting", back_populates="raw_payloads")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_meeting_id", "event_type", name="uq_webhook_events_provider_meeting_event"),
    )

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    provider = Column(String(50), nullable=False)
    provider_meeting_id = Column(String(150), nullable=False)
    event_type = Column(String(100), nullable=False)
    received_at = Column(DateTime, default=_now, nullable=False)
    processed_at = Column(DateTime, nullable=True)


class ProposedTask(Base):
    __tablename__ = "proposed_tasks"
    __table_args__ = (
        UniqueConstraint("meeting_id", "fingerprint", name="uq_proposed_tasks_meeting_fingerprint"),
    )

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(ItemTypeEnum), default=ItemTypeEnum.TASK, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_raw = Column(String(150), nullable=True)
    owner_member_id = Column(String(100), nullable=True)
    deadline_raw = Column(String(100), nullable=True)
    deadline_iso = Column(Date, nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    evidence = Column(Text, nullable=False)
    evidence_start_s = Column(Float, nullable=True)
    ambiguity_flags = Column(JSON, nullable=False, default=list)
    status = Column(Enum(ProposedTaskStatusEnum), default=ProposedTaskStatusEnum.PENDING, nullable=False)
    fingerprint = Column(String(64), nullable=False)
    telegram_message_id = Column(String(100), nullable=True)
    reminder_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    meeting = relationship("Meeting", back_populates="proposed_tasks")
