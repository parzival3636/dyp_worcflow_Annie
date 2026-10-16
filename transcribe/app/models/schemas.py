"""
Pydantic schemas for request/response payloads and LLM extraction contracts.
Matches PRD Section 8 and Section 10.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class AmbiguityFlag(str, enum.Enum):
    NO_OWNER = "NO_OWNER"
    MULTIPLE_OWNERS = "MULTIPLE_OWNERS"
    UNKNOWN_SPEAKER = "UNKNOWN_SPEAKER"
    NO_DEADLINE = "NO_DEADLINE"
    VAGUE_DEADLINE = "VAGUE_DEADLINE"
    VAGUE_SCOPE = "VAGUE_SCOPE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CONDITIONAL = "CONDITIONAL"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"


# ── Endpoint Request/Response Schemas ────────────────────────────────────────

class MeetingCreateRequest(BaseModel):
    meeting_link: str
    project_id: str
    title: Optional[str] = None
    organizer_telegram_id: Optional[str] = None
    meeting_password: Optional[str] = None
    consent_confirmed: bool = False


class MeetingCreateResponse(BaseModel):
    meeting_id: str
    status: str
    normalized_link: str


class MeetingDetailResponse(BaseModel):
    meeting_id: str
    project_id: str
    title: Optional[str] = None
    status: str
    meeting_link: Optional[str] = None
    platform: str
    provider: str
    segment_count: int = 0
    summary: Optional[str] = None
    proposed_tasks_summary: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime


class ProposedTaskResponse(BaseModel):
    id: str
    meeting_id: str
    type: str
    title: str
    description: Optional[str] = None
    owner_raw: Optional[str] = None
    owner_member_id: Optional[str] = None
    deadline_raw: Optional[str] = None
    deadline_iso: Optional[date] = None
    confidence: float
    evidence: str
    evidence_start_s: Optional[float] = None
    ambiguity_flags: List[str] = Field(default_factory=list)
    status: str
    created_at: datetime


class PollResponse(BaseModel):
    meeting_id: str
    status: str


class ReprocessResponse(BaseModel):
    meeting_id: str
    status: str
    tasks_count: int


class FirefliesWebhookPayload(BaseModel):
    meetingId: str
    eventType: str
    clientReferenceId: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    db: str = "ok"


# ── Section 10 LLM Extraction Contracts ──────────────────────────────────────

class ExtractedItem(BaseModel):
    type: Literal["task", "decision", "blocker", "question"]
    title: str = Field(min_length=3, max_length=120)
    description: str = ""
    owner_raw: Optional[str] = None
    deadline_raw: Optional[str] = None
    deadline_iso: Optional[date] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    evidence_start_s: Optional[float] = None
    ambiguity_flags: List[AmbiguityFlag] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    items: List[ExtractedItem] = Field(default_factory=list)
    meeting_summary: str = ""
