"""
Fireflies Webhook API endpoint.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import or_, select
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
from app.models.orm import Meeting, MeetingStatusEnum, PlatformEnum, ProviderEnum
from app.models.schemas import FirefliesWebhookPayload
from app.providers.base import TranscriptProvider
from app.services.meeting_service import process_transcript
from app.services.notifier import Notifier
from app.services.webhook_security import record_event_once, verify_signature

router = APIRouter()
logger = logging.getLogger("transcribe.webhooks")


@router.post("/webhooks/fireflies")
async def handle_fireflies_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: Optional[str] = Header(None),
    session: Session = Depends(get_session),
    provider: TranscriptProvider = Depends(get_provider),
    llm: LLMClient = Depends(get_llm_client),
    notifier: Notifier = Depends(get_notifier),
    member_repo: MemberRepository = Depends(get_member_repo),
):
    """
    Receives Fireflies webhook events.
    Verifies signature, ensures idempotency, and enqueues background processing.
    """
    settings = get_settings()
    raw_body = await request.body()

    # 1. Verify HMAC signature
    is_valid = verify_signature(
        raw_body=raw_body,
        header_value=x_hub_signature,
        secret=settings.FIREFLIES_WEBHOOK_SECRET,
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")

    # 2. Parse JSON
    try:
        body_json = json.loads(raw_body.decode("utf-8"))
        payload = FirefliesWebhookPayload.model_validate(body_json)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Malformed webhook JSON: {e}")

    # 3. Filter event type
    if payload.eventType != "Transcription completed":
        return Response(status_code=status.HTTP_200_OK, content="Event ignored.")

    # 4. Idempotency check
    is_new_event = record_event_once(
        session=session,
        provider="FIREFLIES",
        meeting_id=payload.meetingId,
        event_type=payload.eventType,
    )
    if not is_new_event:
        return Response(status_code=status.HTTP_200_OK, content="Duplicate event ignored.")

    # 5. Match Meeting
    meeting = session.execute(
        select(Meeting).where(
            or_(
                Meeting.provider_meeting_id == payload.meetingId,
                Meeting.client_reference_id == payload.clientReferenceId,
            )
        )
    ).scalars().first()

    if not meeting:
        # Create unlinked meeting
        meeting = Meeting(
            project_id="unlinked",
            title="Unlinked Meeting",
            provider=ProviderEnum.FIREFLIES,
            platform=PlatformEnum.UNKNOWN,
            provider_meeting_id=payload.meetingId,
            status=MeetingStatusEnum.TRANSCRIPT_RECEIVED,
            unlinked=True,
            consent_confirmed=True,
        )
        session.add(meeting)
        session.commit()

    meeting.status = MeetingStatusEnum.TRANSCRIPT_RECEIVED
    meeting.provider_meeting_id = payload.meetingId
    session.add(meeting)
    session.commit()

    # Enqueue background processing
    background_tasks.add_task(
        process_transcript,
        session=session,
        meeting_id=meeting.id,
        provider=provider,
        llm_client=llm,
        member_repo=member_repo,
        notifier=notifier,
    )

    return Response(status_code=status.HTTP_200_OK, content="Webhook accepted.")
