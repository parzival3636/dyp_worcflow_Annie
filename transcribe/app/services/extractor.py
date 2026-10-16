"""
LLM extraction orchestration, deduplication, and post-validation pipeline.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Set
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.config import get_settings
from app.integrations.members import ProjectMember
from app.llm.client import LLMClient, ExtractionError
from app.models.orm import (
    ItemTypeEnum,
    Meeting,
    MeetingStatusEnum,
    ProposedTask,
    ProposedTaskStatusEnum,
    TranscriptSegment,
)
from app.models.schemas import AmbiguityFlag, ExtractedItem, ExtractionResult
from app.services.chunker import chunk_segments
from app.services.date_resolver import resolve_date
from app.services.member_matcher import match_member_from_speaker_or_raw

logger = logging.getLogger("transcribe.extractor")

_PROMPT_DIR = Path(__file__).parent.parent / "llm" / "prompts"


def _load_prompt(filename: str) -> str:
    path = _PROMPT_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _normalize_str(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def compute_fingerprint(owner_raw: Optional[str], title: str) -> str:
    owner_part = (owner_raw or "?").strip().lower()
    title_part = _normalize_str(title)
    return hashlib.sha1(f"{owner_part}|{title_part}".encode("utf-8")).hexdigest()


async def extract_commitments(
    session: Session,
    meeting: Meeting,
    segments: List[TranscriptSegment],
    members: List[ProjectMember],
    llm_client: LLMClient,
) -> List[ProposedTask]:
    """
    Runs token-aware chunking, LLM extraction per chunk, deduplication,
    post-validation, and persists ProposedTask rows.
    """
    settings = get_settings()
    system_prompt = _load_prompt("extraction_system.txt")
    user_template = _load_prompt("extraction_user.txt")

    if not segments or sum(len(s.text.split()) for s in segments) < settings.MIN_TRANSCRIPT_WORDS:
        meeting.status = MeetingStatusEnum.TRANSCRIPT_EMPTY
        session.add(meeting)
        session.commit()
        return []

    # Full text for evidence validation
    full_transcript_text = _normalize_str(" ".join(s.text for s in segments))

    # Formatted member list for LLM context
    member_lines = [
        f"- {m.full_name} (aliases: {', '.join(m.aliases) if m.aliases else 'none'})"
        for m in members
    ]
    members_context = "\n".join(member_lines) if member_lines else "None provided."

    chunks = chunk_segments(segments)
    raw_extracted_items: List[ExtractedItem] = []
    summaries: List[str] = []

    for chunk in chunks:
        user_prompt = user_template.format(
            title=meeting.title or "Project Meeting",
            meeting_date=meeting.meeting_date.isoformat() if meeting.meeting_date else "Today",
            members=members_context,
            transcript_chunk=chunk.formatted_text,
        )

        try:
            result_json = await llm_client.complete_json(
                system=system_prompt,
                user=user_prompt,
                schema=ExtractionResult.model_json_schema(),
            )
            parsed_result = ExtractionResult.model_validate(result_json)
            raw_extracted_items.extend(parsed_result.items)
            if parsed_result.meeting_summary and parsed_result.meeting_summary.strip():
                summaries.append(parsed_result.meeting_summary.strip())
        except Exception as e:
            logger.error("LLM extraction failed on chunk %d: %s", chunk.chunk_index, e)
            raise ExtractionError(f"LLM extraction failure: {e}")

    # Deduplicate across chunks (same intent & owner)
    deduped_items: List[ExtractedItem] = []
    for item in raw_extracted_items:
        is_dup = False
        for existing in deduped_items:
            same_owner = (item.owner_raw or "").lower() == (existing.owner_raw or "").lower()
            similarity = fuzz.token_sort_ratio(item.title.lower(), existing.title.lower())
            if same_owner and similarity >= 90:
                is_dup = True
                # Merge: keep highest confidence
                if item.confidence > existing.confidence:
                    existing.confidence = item.confidence
                    existing.evidence = item.evidence
                break
        if not is_dup:
            deduped_items.append(item)

    # Post-validation and persistence
    persisted_tasks: List[ProposedTask] = []
    for item in deduped_items:
        ambiguity_flags: Set[str] = {f.value for f in item.ambiguity_flags}
        evidence_clean = _normalize_str(item.evidence)

        # 1. Evidence substring check
        if evidence_clean not in full_transcript_text:
            item.confidence = min(item.confidence, 0.4)
            ambiguity_flags.add(AmbiguityFlag.LOW_CONFIDENCE.value)

        # 2. Member matching
        # Look up speaker if evidence contains first-person pronoun
        matching_seg = next((s for s in segments if evidence_clean and evidence_clean in _normalize_str(s.text)), None)
        speaker_raw = matching_seg.speaker_raw if matching_seg else None
        match_res = match_member_from_speaker_or_raw(
            owner_raw=item.owner_raw,
            speaker_raw=speaker_raw,
            evidence=item.evidence,
            members=members,
        )

        owner_member_id = match_res.member.member_id if match_res.member else None
        if match_res.flag:
            ambiguity_flags.add(match_res.flag.value)
        if not item.owner_raw and not owner_member_id:
            ambiguity_flags.add(AmbiguityFlag.NO_OWNER.value)

        # 3. Date resolution
        resolved_date, date_flag = resolve_date(
            item.deadline_raw,
            meeting.meeting_date,
            settings.DEFAULT_TIMEZONE,
        )
        if date_flag:
            ambiguity_flags.add(date_flag.value)

        # Check if deadline resolved before meeting date
        if resolved_date and meeting.meeting_date and resolved_date < meeting.meeting_date.date():
            resolved_date = None
            ambiguity_flags.add(AmbiguityFlag.VAGUE_DEADLINE.value)

        if not item.deadline_raw and item.type == "task":
            ambiguity_flags.add(AmbiguityFlag.NO_DEADLINE.value)

        # 4. Fingerprint computation
        fingerprint = compute_fingerprint(item.owner_raw, item.title)

        # 5. Determine status
        status = ProposedTaskStatusEnum.PENDING
        if item.confidence < settings.CONFIDENCE_THRESHOLD:
            status = ProposedTaskStatusEnum.LOW_CONFIDENCE_HIDDEN
        elif any(
            flag in ambiguity_flags
            for flag in (
                AmbiguityFlag.NO_OWNER.value,
                AmbiguityFlag.MULTIPLE_OWNERS.value,
                AmbiguityFlag.UNKNOWN_SPEAKER.value,
                AmbiguityFlag.VAGUE_DEADLINE.value,
                AmbiguityFlag.NO_DEADLINE.value,
                AmbiguityFlag.VAGUE_SCOPE.value,
            )
        ):
            status = ProposedTaskStatusEnum.NEEDS_CLARIFICATION

        type_map = {
            "task": ItemTypeEnum.TASK,
            "decision": ItemTypeEnum.DECISION,
            "blocker": ItemTypeEnum.BLOCKER,
            "question": ItemTypeEnum.QUESTION,
        }

        # Check if proposed task with same fingerprint already exists for this meeting
        existing_task = (
            session.query(ProposedTask)
            .filter(ProposedTask.meeting_id == meeting.id, ProposedTask.fingerprint == fingerprint)
            .first()
        )

        if existing_task:
            # Idempotent update
            existing_task.confidence = max(existing_task.confidence, item.confidence)
            existing_task.evidence = item.evidence
            existing_task.ambiguity_flags = list(ambiguity_flags)
            session.add(existing_task)
            persisted_tasks.append(existing_task)
        else:
            task = ProposedTask(
                meeting_id=meeting.id,
                type=type_map.get(item.type, ItemTypeEnum.TASK),
                title=item.title,
                description=item.description,
                owner_raw=item.owner_raw,
                owner_member_id=owner_member_id,
                deadline_raw=item.deadline_raw,
                deadline_iso=resolved_date,
                confidence=item.confidence,
                evidence=item.evidence,
                evidence_start_s=item.evidence_start_s,
                ambiguity_flags=list(ambiguity_flags),
                status=status,
                fingerprint=fingerprint,
            )
            session.add(task)
            persisted_tasks.append(task)

    if summaries:
        meeting.summary = " ".join(summaries)
    meeting.status = MeetingStatusEnum.EXTRACTED
    session.add(meeting)
    session.commit()
    return persisted_tasks
