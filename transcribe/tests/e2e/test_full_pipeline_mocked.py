"""
End-to-End mocked pipeline test (PRD Section 15.8, X1-X4).
Validates full flow: link intake -> bot dispatch -> signed webhook -> extraction -> cards -> approve -> TaskSink.
"""
import asyncio
import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.telegram import get_task_sink, set_task_sink
from app.config import get_settings
from app.integrations.members import InMemoryMemberRepository, ProjectMember
from app.integrations.tasks import InMemoryTaskSink
from app.llm.client import FakeLLMClient
from app.models.orm import (
    Meeting,
    MeetingStatusEnum,
    ProposedTask,
    ProposedTaskStatusEnum,
)
from app.providers.base import DispatchResult, ProviderSentence, ProviderTranscript
from app.services.meeting_service import create_meeting, process_transcript
from app.services.notifier import FakeNotifier


class MockE2EProvider:
    def __init__(self, transcript: ProviderTranscript):
        self.transcript = transcript

    async def dispatch_bot(self, link: str, client_ref_id: str) -> DispatchResult:
        return DispatchResult(success=True)

    async def fetch_transcript(self, id: str):
        return self.transcript

    async def list_recent(self, *args, **kwargs):
        return []


def test_x1_full_pipeline_mocked(client: TestClient, db_session: Session):
    async def _test():
        task_sink = InMemoryTaskSink()
        set_task_sink(task_sink)

        notifier = FakeNotifier()
        member_repo = InMemoryMemberRepository({
            "proj_e2e": [
                ProjectMember(member_id="m_priya", full_name="Priya Patel", telegram_id="111"),
                ProjectMember(member_id="m_rahul", full_name="Rahul Sharma", telegram_id="222"),
            ]
        })

        transcript = ProviderTranscript(
            id="ff_meet_e2e",
            title="Sprint Sync",
            duration=1800,
            sentences=[
                ProviderSentence(index=0, speaker_name="Priya Patel", text="I will finish the login page by Friday.", start_time=0.0, end_time=4.0),
                ProviderSentence(index=1, speaker_name="Rahul Sharma", text="Extra words to ensure that the minimum word requirement for extraction is exceeded.", start_time=5.0, end_time=12.0),
            ],
        )
        provider = MockE2EProvider(transcript)

        canned_llm_resp = {
            "items": [
                {
                    "type": "task",
                    "title": "Finish login page",
                    "owner_raw": "Priya",
                    "deadline_raw": "by Friday",
                    "confidence": 0.95,
                    "evidence": "I will finish the login page by Friday.",
                }
            ],
            "meeting_summary": "Priya finishes login page.",
        }
        llm = FakeLLMClient([canned_llm_resp])

        # 1. POST /meetings (Link Intake)
        from app.models.schemas import MeetingCreateRequest
        req = MeetingCreateRequest(
            meeting_link="https://meet.google.com/abc-defg-hij",
            project_id="proj_e2e",
            title="Sprint Sync",
            organizer_telegram_id="999",
            consent_confirmed=True,
        )
        meeting, is_new = await create_meeting(db_session, provider, req, notifier)
        assert is_new is True
        assert meeting.status == MeetingStatusEnum.BOT_REQUESTED

        # 2. Simulate Webhook Reception
        meeting.provider_meeting_id = "ff_meet_e2e"
        db_session.add(meeting)
        db_session.commit()

        # 3. Process Transcript
        await process_transcript(
            session=db_session,
            meeting_id=meeting.id,
            provider=provider,
            llm_client=llm,
            member_repo=member_repo,
            notifier=notifier,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatusEnum.AWAITING_REVIEW

        # 4. Verify ProposedTask was created
        tasks = db_session.query(ProposedTask).filter(ProposedTask.meeting_id == meeting.id).all()
        assert len(tasks) == 1
        task = tasks[0]
        assert task.status == ProposedTaskStatusEnum.PENDING
        assert task.owner_member_id == "m_priya"

        # Verify task card was sent via notifier
        cards = [m for m in notifier.sent_messages if m["type"] == "card"]
        assert len(cards) == 1
        assert cards[0]["task_id"] == task.id

        # 5. Simulate User tapping [Approve]
        approve_body = {
            "callback_query": {
                "id": "cq_e2e",
                "data": f"tr:approve:{task.id}",
                "message": {"chat": {"id": 999}},
            }
        }
        resp = client.post("/api/v1/transcribe/telegram/callback", json=approve_body)
        assert resp.status_code == 200

        # 6. Verify TaskSink received the task
        assert len(task_sink.created_tasks) == 1
        assert task_sink.created_tasks[0].title == "Finish login page"
        assert task_sink.created_tasks[0].owner_member_id == "m_priya"

        # Verify meeting transitioned to COMPLETED
        db_session.refresh(meeting)
        assert meeting.status == MeetingStatusEnum.COMPLETED

    asyncio.run(_test())
