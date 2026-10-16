"""
Meetings REST API endpoints.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_llm_client,
    get_member_repo,
    get_notifier,
    get_provider,
    get_session,
)
from app.config import get_settings
from app.integrations.members import MemberRepository
from app.llm.client import LLMClient
from app.models.orm import (
    Meeting,
    MeetingStatusEnum,
    PlatformEnum,
    ProposedTask,
    ProposedTaskStatusEnum,
    ProviderEnum,
    RawPayload,
    TranscriptSegment,
)
from app.models.schemas import (
    MeetingCreateRequest,
    MeetingCreateResponse,
    MeetingDetailResponse,
    PollResponse,
    ProposedTaskResponse,
    ReprocessResponse,
)
from app.providers.base import TranscriptProvider
from app.providers.fireflies import ProviderError
from app.providers.upload import parse_upload
from app.services.extractor import extract_commitments
from app.services.link_validator import InvalidMeetingLink
from app.services.meeting_service import create_meeting, process_transcript
from app.services.normalizer import normalize_transcript
from app.services.notifier import Notifier

router = APIRouter()

# In-memory per-project rate limiting (5 req / min)
_rate_limits = defaultdict(list)


def _check_rate_limit(project_id: str):
    now = time.time()
    timestamps = _rate_limits[project_id]
    _rate_limits[project_id] = [t for t in timestamps if now - t < 60.0]
    if len(_rate_limits[project_id]) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 meeting creations per minute per project.",
        )
    _rate_limits[project_id].append(now)


@router.get("/health")
async def transcribe_health():
    return JSONResponse({"status": "ok", "service": "transcribe"})


@router.post("/meetings", response_model=MeetingCreateResponse)
async def create_new_meeting(
    payload: MeetingCreateRequest,
    session: Session = Depends(get_session),
    provider: TranscriptProvider = Depends(get_provider),
    notifier: Notifier = Depends(get_notifier),
):
    _check_rate_limit(payload.project_id)

    try:
        meeting, is_new = await create_meeting(
            session=session,
            provider=provider,
            payload=payload,
            notifier=notifier,
        )
    except InvalidMeetingLink as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ProviderError as e:
        if e.code == "RATE_LIMIT":
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=e.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Provider error: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unexpected error: {e}")

    status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK

    return JSONResponse(
        status_code=status_code,
        content={
            "meeting_id": meeting.id,
            "status": meeting.status.value,
            "normalized_link": meeting.meeting_link or "",
        },
    )


@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
def get_meeting(meeting_id: str, session: Session = Depends(get_session)):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    seg_count = session.query(func.count(TranscriptSegment.id)).filter(TranscriptSegment.meeting_id == meeting.id).scalar() or 0

    tasks = session.query(ProposedTask).filter(ProposedTask.meeting_id == meeting.id).all()
    summary = {}
    for t in tasks:
        summary[t.type.value] = summary.get(t.type.value, 0) + 1

    return MeetingDetailResponse(
        meeting_id=meeting.id,
        project_id=meeting.project_id,
        title=meeting.title,
        status=meeting.status.value,
        meeting_link=meeting.meeting_link,
        platform=meeting.platform.value,
        provider=meeting.provider.value,
        segment_count=seg_count,
        summary=meeting.summary,
        proposed_tasks_summary=summary,
        created_at=meeting.created_at,
    )


@router.get("/meetings/{meeting_id}/tasks", response_model=List[ProposedTaskResponse])
def get_meeting_tasks(
    meeting_id: str,
    status: Optional[str] = Query(None),
    include_low_confidence: bool = Query(False),
    session: Session = Depends(get_session),
):
    query = session.query(ProposedTask).filter(ProposedTask.meeting_id == meeting_id)
    if status:
        query = query.filter(ProposedTask.status == status)
    if not include_low_confidence:
        query = query.filter(ProposedTask.status != ProposedTaskStatusEnum.LOW_CONFIDENCE_HIDDEN)

    tasks = query.order_by(ProposedTask.created_at.asc()).all()
    return [
        ProposedTaskResponse(
            id=t.id,
            meeting_id=t.meeting_id,
            type=t.type.value,
            title=t.title,
            description=t.description,
            owner_raw=t.owner_raw,
            owner_member_id=t.owner_member_id,
            deadline_raw=t.deadline_raw,
            deadline_iso=t.deadline_iso,
            confidence=t.confidence,
            evidence=t.evidence,
            evidence_start_s=t.evidence_start_s,
            ambiguity_flags=t.ambiguity_flags or [],
            status=t.status.value,
            created_at=t.created_at,
        )
        for t in tasks
    ]


@router.post("/meetings/{meeting_id}/poll", response_model=PollResponse)
async def force_poll_meeting(
    meeting_id: str,
    fireflies_meeting_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    provider: TranscriptProvider = Depends(get_provider),
    llm: LLMClient = Depends(get_llm_client),
    notifier: Notifier = Depends(get_notifier),
    member_repo: MemberRepository = Depends(get_member_repo),
):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if fireflies_meeting_id:
        meeting.provider_meeting_id = fireflies_meeting_id
        session.add(meeting)
        session.commit()

    await process_transcript(
        session=session,
        meeting_id=meeting.id,
        provider=provider,
        llm_client=llm,
        member_repo=member_repo,
        notifier=notifier,
    )
    session.refresh(meeting)
    return PollResponse(meeting_id=meeting.id, status=meeting.status.value)


@router.post("/meetings/{meeting_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_meeting(
    meeting_id: str,
    session: Session = Depends(get_session),
    llm: LLMClient = Depends(get_llm_client),
    member_repo: MemberRepository = Depends(get_member_repo),
):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    raw_payload_row = session.query(RawPayload).filter(RawPayload.meeting_id == meeting.id).first()
    if not raw_payload_row:
        raise HTTPException(status_code=400, detail="No stored raw payload found for this meeting.")

    from app.providers.base import ProviderTranscript
    transcript = ProviderTranscript.model_validate(raw_payload_row.payload_json)

    # Re-normalize
    segments = normalize_transcript(transcript, meeting_id=meeting.id)
    members = member_repo.get_project_members(meeting.project_id)
    tasks = await extract_commitments(
        session=session,
        meeting=meeting,
        segments=segments,
        members=members,
        llm_client=llm,
    )

    return ReprocessResponse(meeting_id=meeting.id, status=meeting.status.value, tasks_count=len(tasks))


@router.post("/meetings/upload")
async def upload_meeting_transcript(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    title: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    organizer_telegram_id: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    llm: LLMClient = Depends(get_llm_client),
    member_repo: MemberRepository = Depends(get_member_repo),
):
    content = await file.read()
    try:
        provider_transcript = parse_upload(content, file.filename or "transcript.txt", title=title)
    except ValueError as e:
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if "exceeds" in str(e) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=str(e))

    m_date = None
    if meeting_date:
        try:
            m_date = datetime.fromisoformat(meeting_date)
        except Exception:
            pass

    meeting = Meeting(
        project_id=project_id,
        title=title or file.filename,
        platform=PlatformEnum.UPLOAD,
        provider=ProviderEnum.UPLOAD,
        organizer_telegram_id=organizer_telegram_id,
        consent_confirmed=True,
        meeting_date=m_date or datetime.now(timezone.utc),
        status=MeetingStatusEnum.TRANSCRIPT_RECEIVED,
    )
    session.add(meeting)
    session.commit()

    # Store raw payload
    raw_payload = RawPayload(
        meeting_id=meeting.id,
        provider="UPLOAD",
        payload_json=provider_transcript.model_dump(),
    )
    session.add(raw_payload)

    segments = normalize_transcript(provider_transcript, meeting_id=meeting.id)
    for seg in segments:
        session.add(seg)
    session.commit()

    members = member_repo.get_project_members(meeting.project_id)
    tasks = await extract_commitments(
        session=session,
        meeting=meeting,
        segments=segments,
        members=members,
        llm_client=llm,
    )

    return {"meeting_id": meeting.id, "status": meeting.status.value, "tasks_extracted": len(tasks)}


@router.delete("/meetings/{meeting_id}")
def delete_meeting_transcript(meeting_id: str, session: Session = Depends(get_session)):
    """Deletes all transcript data for a meeting on request (PRD Section 11)."""
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    session.delete(meeting)
    session.commit()
    return {"status": "ok", "deleted_meeting_id": meeting_id}
