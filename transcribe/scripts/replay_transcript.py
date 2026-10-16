"""
Re-runs normalization and extraction on a stored raw payload without calling Fireflies.
"""
from __future__ import annotations

import argparse
import asyncio
from app.db import get_session_factory
from app.integrations.members import InMemoryMemberRepository
from app.llm.client import HttpLLMClient
from app.models.orm import Meeting, RawPayload
from app.providers.base import ProviderTranscript
from app.services.extractor import extract_commitments
from app.services.normalizer import normalize_transcript


async def replay(meeting_id: str):
    SessionLocal = get_session_factory()
    session = SessionLocal()

    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        print(f"Meeting {meeting_id} not found.")
        return

    raw = session.query(RawPayload).filter(RawPayload.meeting_id == meeting.id).first()
    if not raw:
        print("No raw payload found.")
        return

    transcript = ProviderTranscript.model_validate(raw.payload_json)
    segments = normalize_transcript(transcript, meeting_id=meeting.id)
    tasks = await extract_commitments(
        session=session,
        meeting=meeting,
        segments=segments,
        members=[],
        llm_client=HttpLLMClient(),
    )
    print(f"Replay complete! Extracted {len(tasks)} proposed tasks.")
    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--meeting-id", required=True, help="Meeting UUID")
    args = parser.parse_args()
    asyncio.run(replay(args.meeting_id))
