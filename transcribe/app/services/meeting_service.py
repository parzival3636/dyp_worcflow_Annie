"""
Meeting service orchestration, status transitions, and lifecycle management.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.integrations.members import MemberRepository, InMemoryMemberRepository
from app.integrations.tasks import TaskSink, InMemoryTaskSink
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
from app.models.schemas import MeetingCreateRequest
from app.providers.base import TranscriptProvider
from app.providers.fireflies import ProviderError
from app.services.extractor import extract_commitments
from app.services.link_validator import validate_and_normalize, InvalidMeetingLink
from app.services.normalizer import normalize_transcript
from app.services.notifier import Notifier

logger = logging.getLogger("transcribe.meeting_service")

# Allowed transitions graph per PRD Section 4.8
ALLOWED_TRANSITIONS = {
    MeetingStatusEnum.BOT_REQUESTED: {
        MeetingStatusEnum.IN_PROGRESS,
        MeetingStatusEnum.TRANSCRIPT_RECEIVED,
        MeetingStatusEnum.DISPATCH_FAILED,
        MeetingStatusEnum.EXPIRED,
    },
    MeetingStatusEnum.IN_PROGRESS: {
        MeetingStatusEnum.TRANSCRIPT_RECEIVED,
        MeetingStatusEnum.EXPIRED,
    },
    MeetingStatusEnum.TRANSCRIPT_RECEIVED: {
        MeetingStatusEnum.PROCESSING,
        MeetingStatusEnum.TRANSCRIPT_EMPTY,
        MeetingStatusEnum.PROCESSING_FAILED,
    },
    MeetingStatusEnum.PROCESSING: {
        MeetingStatusEnum.EXTRACTED,
        MeetingStatusEnum.PROCESSING_FAILED,
    },
    MeetingStatusEnum.EXTRACTED: {
        MeetingStatusEnum.AWAITING_REVIEW,
        MeetingStatusEnum.COMPLETED,
    },
    MeetingStatusEnum.AWAITING_REVIEW: {
        MeetingStatusEnum.COMPLETED,
    },
    # Final states have no further transitions
    MeetingStatusEnum.COMPLETED: set(),
    MeetingStatusEnum.DISPATCH_FAILED: set(),
    MeetingStatusEnum.TRANSCRIPT_EMPTY: set(),
    MeetingStatusEnum.PROCESSING_FAILED: set(),
    MeetingStatusEnum.EXPIRED: set(),
}


def transition(meeting: Meeting, new_status: MeetingStatusEnum):
    """Enforces valid status transitions according to PRD Section 4.8."""
    if meeting.status == new_status:
        return
    allowed = ALLOWED_TRANSITIONS.get(meeting.status, set())
    if new_status not in allowed:
        raise ValueError(f"Illegal meeting status transition: {meeting.status} -> {new_status}")
    meeting.status = new_status
    meeting.updated_at = datetime.now(timezone.utc)


async def create_meeting(
    session: Session,
    provider: TranscriptProvider,
    payload: MeetingCreateRequest,
    notifier: Optional[Notifier] = None,
) -> Tuple[Meeting, bool]:
    """
    Intakes meeting link, verifies consent, deduplicates, and dispatches bot.
    Returns (Meeting, is_new: bool).
    """
    if not payload.consent_confirmed:
        raise ValueError("Consent must be confirmed before dispatching notetaker bot.")

    norm = validate_and_normalize(payload.meeting_link)
    settings = get_settings()

    # Deduplication check: same link + project within window, non-failed status
    dedup_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.MEETING_DEDUP_WINDOW_HOURS)
    existing = session.execute(
        select(Meeting).where(
            and_(
                Meeting.project_id == payload.project_id,
                Meeting.meeting_link == norm.url,
                Meeting.created_at >= dedup_cutoff,
                Meeting.status.notin_([MeetingStatusEnum.DISPATCH_FAILED, MeetingStatusEnum.EXPIRED]),
            )
        )
    ).scalars().first()

    if existing:
        return existing, False

    client_ref_id = str(uuid.uuid4())
    meeting = Meeting(
        project_id=payload.project_id,
        title=payload.title or "Project Meeting",
        meeting_link=norm.url,
        platform=norm.platform,
        provider=ProviderEnum.FIREFLIES,
        client_reference_id=client_ref_id,
        organizer_telegram_id=payload.organizer_telegram_id,
        consent_confirmed=True,
        status=MeetingStatusEnum.BOT_REQUESTED,
    )
    session.add(meeting)
    session.commit()

    # Call provider dispatch
    try:
        dispatch_res = await provider.dispatch_bot(norm.url, client_ref_id)
        if not dispatch_res.success:
            meeting.status = MeetingStatusEnum.DISPATCH_FAILED
            meeting.error_detail = dispatch_res.detail or "Bot dispatch failed."
            session.add(meeting)
            session.commit()
            if notifier and meeting.organizer_telegram_id:
                await notifier.send_text(
                    meeting.organizer_telegram_id,
                    "⚠️ Could not dispatch Fireflies notetaker bot to your meeting.",
                )
        else:
            if notifier and meeting.organizer_telegram_id:
                await notifier.send_text(
                    meeting.organizer_telegram_id,
                    "🤖 Fireflies bot is joining. Please admit *Fireflies Notetaker* from the waiting room.",
                )
    except Exception as exc:
        meeting.status = MeetingStatusEnum.DISPATCH_FAILED
        meeting.error_detail = str(exc)
        session.add(meeting)
        session.commit()
        if notifier and meeting.organizer_telegram_id:
            await notifier.send_text(
                meeting.organizer_telegram_id,
                f"⚠️ Error dispatching bot: {exc}",
            )
        raise exc

    return meeting, True


async def process_transcript(
    session: Session,
    meeting_id: str,
    provider: TranscriptProvider,
    llm_client: LLMClient,
    member_repo: Optional[MemberRepository] = None,
    notifier: Optional[Notifier] = None,
    retry_interval_s: float = 0.1,  # Fast for tests, configurable in prod
):
    """
    Fetches transcript from provider (with retry loop if not ready),
    normalizes, extracts commitments, and notifies organizer.
    """
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        logger.error("Meeting %s not found for processing", meeting_id)
        return

    meeting.status = MeetingStatusEnum.PROCESSING
    session.add(meeting)
    session.commit()

    try:
        provider_id = meeting.provider_meeting_id
        if not provider_id:
            try:
                recents = await provider.list_recent(limit=10)
                matched = None
                # 1. Match by meeting_link if available
                if meeting.meeting_link and recents:
                    target_link = meeting.meeting_link.strip().rstrip("/").lower()
                    for r in recents:
                        r_link = (r.meeting_link or "").strip().rstrip("/").lower()
                        if r_link and r_link == target_link:
                            matched = r
                            break

                # 2. If no exact link match, pick newest transcript by date/timestamp
                if not matched and recents:
                    def _get_ts(item):
                        try:
                            return float(item.date or 0)
                        except Exception:
                            return 0
                    sorted_recents = sorted(recents, key=_get_ts, reverse=True)
                    matched = sorted_recents[0]

                if matched:
                    provider_id = matched.id
                    meeting.provider_meeting_id = provider_id
                    session.add(meeting)
                    session.commit()
            except Exception as e:
                logger.warning("Could not list or match recent transcripts: %s", e)
        if not provider_id:
            provider_id = meeting.client_reference_id

        transcript = None

        # Transcript readiness retry loop (up to 5 attempts)
        for _ in range(5):
            transcript = await provider.fetch_transcript(provider_id)
            if transcript and transcript.sentences:
                break
            await asyncio.sleep(retry_interval_s)

        if not transcript or not transcript.sentences:
            meeting.status = MeetingStatusEnum.PROCESSING_FAILED
            meeting.error_detail = "Transcript was not ready or contained no sentences."
            session.add(meeting)
            session.commit()
            if notifier and meeting.organizer_telegram_id:
                await notifier.send_text(
                    meeting.organizer_telegram_id,
                    "⚠️ Could not process transcript: Transcript was empty or not ready.",
                )
            return

        # Store raw payload
        raw_payload = RawPayload(
            meeting_id=meeting.id,
            provider="FIREFLIES",
            payload_json=transcript.model_dump(),
        )
        session.add(raw_payload)

        # Normalize segments
        segments = normalize_transcript(transcript, meeting_id=meeting.id)
        for seg in segments:
            session.add(seg)
        session.commit()

        # Update meeting metadata
        if transcript.duration:
            meeting.duration_s = transcript.duration
        if transcript.title and not meeting.title:
            meeting.title = transcript.title

        # Extraction
        members = member_repo.get_project_members(meeting.project_id) if member_repo else []
        proposed_tasks = await extract_commitments(session, meeting, segments, members, llm_client)

        # Notify via Telegram
        if notifier and meeting.organizer_telegram_id:
            pending_count = sum(1 for t in proposed_tasks if t.status == ProposedTaskStatusEnum.PENDING)
            clarify_count = sum(1 for t in proposed_tasks if t.status == ProposedTaskStatusEnum.NEEDS_CLARIFICATION)
            summary_part = f"• Summary: {meeting.summary}\n" if meeting.summary else ""
            summary_msg = (
                f"📝 *Meeting Extracted:* {meeting.title or 'Meeting'}\n"
                f"{summary_part}"
                f"• Duration: {meeting.duration_s or 0}s\n"
                f"• Proposed Tasks: {len(proposed_tasks)} ({pending_count} ready, {clarify_count} need clarification)"
            )
            await notifier.send_text(meeting.organizer_telegram_id, summary_msg)

            for task in proposed_tasks:
                if task.status == ProposedTaskStatusEnum.PENDING:
                    msg_id = await notifier.send_task_card(meeting.organizer_telegram_id, task)
                    task.telegram_message_id = msg_id
                elif task.status == ProposedTaskStatusEnum.NEEDS_CLARIFICATION:
                    first_flag = task.ambiguity_flags[0] if task.ambiguity_flags else "UNKNOWN"
                    q = f"Who owns the task '{task.title}'?" if "OWNER" in first_flag else f"When is '{task.title}' due?"
                    msg_id = await notifier.send_clarification(meeting.organizer_telegram_id, task, q)
                    task.telegram_message_id = msg_id
            session.commit()

        meeting.status = MeetingStatusEnum.AWAITING_REVIEW
        session.add(meeting)
        session.commit()

    except Exception as exc:
        logger.exception("Error processing transcript for meeting %s", meeting_id)
        meeting.status = MeetingStatusEnum.PROCESSING_FAILED
        meeting.error_detail = str(exc)
        session.add(meeting)
        session.commit()
        if notifier and meeting.organizer_telegram_id:
            await notifier.send_text(
                meeting.organizer_telegram_id,
                f"⚠️ Error processing meeting transcript: {exc}",
            )
