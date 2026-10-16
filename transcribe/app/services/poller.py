"""
Background poller for pending meetings.
Checks recent transcripts and marks timed-out meetings as EXPIRED.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.integrations.members import MemberRepository
from app.llm.client import LLMClient
from app.models.orm import Meeting, MeetingStatusEnum
from app.providers.base import TranscriptProvider
from app.services.meeting_service import process_transcript
from app.services.notifier import Notifier

logger = logging.getLogger("transcribe.poller")


async def poll_pending_meetings(
    session: Session,
    provider: TranscriptProvider,
    llm_client: LLMClient,
    member_repo: Optional[MemberRepository] = None,
    notifier: Optional[Notifier] = None,
):
    """
    Polls meetings in BOT_REQUESTED or IN_PROGRESS.
    Expires meetings older than MEETING_EXPIRE_HOURS (default 6h).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire_cutoff = now - timedelta(hours=settings.MEETING_EXPIRE_HOURS)

    pending_meetings = session.execute(
        select(Meeting).where(
            Meeting.status.in_([MeetingStatusEnum.BOT_REQUESTED, MeetingStatusEnum.IN_PROGRESS])
        )
    ).scalars().all()

    for meeting in pending_meetings:
        # Check expiration
        if meeting.created_at < expire_cutoff:
            meeting.status = MeetingStatusEnum.EXPIRED
            meeting.error_detail = "Meeting expired after 6 hours without completed transcript."
            session.add(meeting)
            session.commit()
            if notifier and meeting.organizer_telegram_id:
                await notifier.send_text(
                    meeting.organizer_telegram_id,
                    f"⏰ Meeting '{meeting.title or meeting.id}' expired: No transcript arrived within 6 hours.",
                )
            continue

        # Check if transcript is ready
        target_id = meeting.provider_meeting_id
        if not target_id:
            try:
                recents = await provider.list_recent(limit=10)
                matched = None
                if meeting.meeting_link and recents:
                    target_link = meeting.meeting_link.strip().rstrip("/").lower()
                    for r in recents:
                        r_link = (r.meeting_link or "").strip().rstrip("/").lower()
                        if r_link and r_link == target_link:
                            matched = r
                            break

                if not matched and recents:
                    def _get_ts(item):
                        try:
                            return float(item.date or 0)
                        except Exception:
                            return 0
                    sorted_recents = sorted(recents, key=_get_ts, reverse=True)
                    matched = sorted_recents[0]

                if matched:
                    target_id = matched.id
                    meeting.provider_meeting_id = target_id
                    session.add(meeting)
                    session.commit()
            except Exception as e:
                logger.warning("Could not list recent transcripts in poller: %s", e)
        if not target_id:
            target_id = meeting.client_reference_id

        try:
            transcript = await provider.fetch_transcript(target_id)
            if transcript and transcript.sentences:
                meeting.status = MeetingStatusEnum.TRANSCRIPT_RECEIVED
                meeting.provider_meeting_id = transcript.id
                session.add(meeting)
                session.commit()

                await process_transcript(
                    session=session,
                    meeting_id=meeting.id,
                    provider=provider,
                    llm_client=llm_client,
                    member_repo=member_repo,
                    notifier=notifier,
                )
        except Exception as e:
            logger.warning("Poller check failed for meeting %s: %s", meeting.id, e)
