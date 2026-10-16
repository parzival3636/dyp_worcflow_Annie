"""
Unit tests for LLM extraction and post-validation (PRD Section 15.6, E1-E14).
"""
import asyncio
import pytest
from sqlalchemy.orm import Session
from app.integrations.members import ProjectMember
from app.llm.client import FakeLLMClient
from app.models.orm import Meeting, MeetingStatusEnum, ProposedTask, ProposedTaskStatusEnum, TranscriptSegment
from app.services.extractor import extract_commitments

MEMBERS = [
    ProjectMember(member_id="m1", full_name="Priya Patel", aliases=["pri"]),
    ProjectMember(member_id="m2", full_name="Rahul Sharma", aliases=["kabs"]),
]


def test_e1_clean_extraction_pending_status(db_session: Session):
    async def _test():
        meeting = Meeting(project_id="proj_e1", status=MeetingStatusEnum.PROCESSING, consent_confirmed=True)
        db_session.add(meeting)
        db_session.commit()

        segments = [
            TranscriptSegment(idx=0, speaker_raw="Priya Patel", text="I will finish the login page by Friday.", start_s=0.0, end_s=3.0),
            TranscriptSegment(idx=1, speaker_raw="Rahul Sharma", text="Great work team.", start_s=4.0, end_s=6.0),
            TranscriptSegment(idx=2, speaker_raw="Rahul Sharma", text="Extra dialogue to meet the minimum word requirement for transcript extraction.", start_s=7.0, end_s=12.0),
        ]

        llm = FakeLLMClient([
            {
                "items": [
                    {
                        "type": "task",
                        "title": "Finish the login page",
                        "owner_raw": "Priya",
                        "deadline_raw": "by Friday",
                        "confidence": 0.95,
                        "evidence": "I will finish the login page by Friday.",
                    }
                ],
                "meeting_summary": "Priya will finish login.",
            }
        ])

        tasks = await extract_commitments(db_session, meeting, segments, MEMBERS, llm)
        assert len(tasks) == 1
        assert tasks[0].status == ProposedTaskStatusEnum.PENDING
        assert tasks[0].owner_member_id == "m1"

    asyncio.run(_test())


def test_e2_no_owner_needs_clarification(db_session: Session):
    async def _test():
        meeting = Meeting(project_id="proj_e2", consent_confirmed=True)
        db_session.add(meeting)
        db_session.commit()

        segments = [
            TranscriptSegment(idx=0, speaker_raw="Rahul", text="Someone should write the project documentation.", start_s=0.0, end_s=3.0),
            TranscriptSegment(idx=1, speaker_raw="Rahul", text="Extra words to ensure that the minimum word requirement for the extraction filter is fully satisfied.", start_s=4.0, end_s=10.0),
        ]

        llm = FakeLLMClient([
            {
                "items": [
                    {
                        "type": "task",
                        "title": "Write project documentation",
                        "owner_raw": None,
                        "deadline_raw": "by tomorrow",
                        "confidence": 0.9,
                        "evidence": "Someone should write the project documentation.",
                    }
                ]
            }
        ])

        tasks = await extract_commitments(db_session, meeting, segments, MEMBERS, llm)
        assert len(tasks) == 1
        assert "NO_OWNER" in tasks[0].ambiguity_flags
        assert tasks[0].status == ProposedTaskStatusEnum.NEEDS_CLARIFICATION

    asyncio.run(_test())


def test_e4_hallucinated_evidence_demoted(db_session: Session):
    async def _test():
        meeting = Meeting(project_id="proj_e4", consent_confirmed=True)
        db_session.add(meeting)
        db_session.commit()

        segments = [
            TranscriptSegment(idx=0, speaker_raw="Rahul", text="Let us review our plans and complete twenty words minimum check.", start_s=0.0, end_s=4.0),
            TranscriptSegment(idx=1, speaker_raw="Priya", text="Yes absolutely let us do that right now team.", start_s=5.0, end_s=8.0),
        ]

        llm = FakeLLMClient([
            {
                "items": [
                    {
                        "type": "task",
                        "title": "Build rocket ship",
                        "owner_raw": "Rahul",
                        "deadline_raw": "soon",
                        "confidence": 0.95,
                        "evidence": "I said I will build a rocket ship today.",  # Hallucinated!
                    }
                ]
            }
        ])

        tasks = await extract_commitments(db_session, meeting, segments, MEMBERS, llm)
        assert len(tasks) == 1
        assert "LOW_CONFIDENCE" in tasks[0].ambiguity_flags
        assert tasks[0].confidence <= 0.4
        assert tasks[0].status == ProposedTaskStatusEnum.LOW_CONFIDENCE_HIDDEN

    asyncio.run(_test())


def test_e9_fingerprint_idempotency(db_session: Session):
    async def _test():
        meeting = Meeting(project_id="proj_e9", consent_confirmed=True)
        db_session.add(meeting)
        db_session.commit()

        segments = [
            TranscriptSegment(idx=0, speaker_raw="Priya Patel", text="I will finish the login page by Friday.", start_s=0.0, end_s=3.0),
            TranscriptSegment(idx=1, speaker_raw="Rahul", text="Adding more content so the minimum word count check easily passes without skipping.", start_s=4.0, end_s=9.0),
        ]

        canned = {
            "items": [
                {
                    "type": "task",
                    "title": "Finish login page",
                    "owner_raw": "Priya",
                    "deadline_raw": "by Friday",
                    "confidence": 0.9,
                    "evidence": "I will finish the login page by Friday.",
                }
            ]
        }

        llm1 = FakeLLMClient([canned])
        t1 = await extract_commitments(db_session, meeting, segments, MEMBERS, llm1)
        assert len(t1) == 1

        # Second pass with same canned response
        llm2 = FakeLLMClient([canned])
        t2 = await extract_commitments(db_session, meeting, segments, MEMBERS, llm2)
        assert len(t2) == 1

        # Assert total rows in DB is still 1
        all_rows = db_session.query(ProposedTask).filter(ProposedTask.meeting_id == meeting.id).all()
        assert len(all_rows) == 1

    asyncio.run(_test())
