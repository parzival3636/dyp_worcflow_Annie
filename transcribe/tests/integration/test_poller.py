"""
Integration tests for fallback poller (PRD Section 15.4, P1-P3).
"""
import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session
from app.models.orm import Meeting, MeetingStatusEnum
from app.providers.base import ProviderSentence, ProviderTranscript
from app.services.notifier import FakeNotifier
from app.services.poller import poll_pending_meetings
from app.llm.client import FakeLLMClient


class MockPollerProvider:
    def __init__(self, transcript_ready: bool = True):
        self.transcript_ready = transcript_ready

    async def fetch_transcript(self, id: str):
        if not self.transcript_ready:
            return None
        return ProviderTranscript(
            id=id,
            title="Polled Sync",
            sentences=[
                ProviderSentence(index=0, speaker_name="Alice", text="Meeting word padding " * 10, start_time=0.0, end_time=2.0)
            ],
        )

    async def dispatch_bot(self, *args, **kwargs):
        raise NotImplementedError

    async def list_recent(self, *args, **kwargs):
        return []


def test_p1_poller_finds_transcript_processes(db_session: Session):
    async def _test():
        meeting = Meeting(
            project_id="proj_p1",
            status=MeetingStatusEnum.BOT_REQUESTED,
            provider_meeting_id="poll_meet_1",
            consent_confirmed=True,
        )
        db_session.add(meeting)
        db_session.commit()

        provider = MockPollerProvider(transcript_ready=True)
        notifier = FakeNotifier()
        llm = FakeLLMClient([{"items": [], "meeting_summary": "Done"}])

        await poll_pending_meetings(
            session=db_session,
            provider=provider,
            llm_client=llm,
            notifier=notifier,
        )

        db_session.refresh(meeting)
        assert meeting.status in (MeetingStatusEnum.TRANSCRIPT_RECEIVED, MeetingStatusEnum.AWAITING_REVIEW)

    asyncio.run(_test())


def test_p2_meeting_older_than_6h_expires(db_session: Session):
    async def _test():
        old_time = datetime.now(timezone.utc) - timedelta(hours=7)
        meeting = Meeting(
            project_id="proj_p2",
            status=MeetingStatusEnum.BOT_REQUESTED,
            created_at=old_time,
            consent_confirmed=True,
        )
        db_session.add(meeting)
        db_session.commit()

        provider = MockPollerProvider(transcript_ready=False)
        notifier = FakeNotifier()

        await poll_pending_meetings(
            session=db_session,
            provider=provider,
            llm_client=FakeLLMClient(),
            notifier=notifier,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatusEnum.EXPIRED

    asyncio.run(_test())
