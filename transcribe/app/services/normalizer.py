"""
Transcript normalization pipeline.
Merges consecutive same-speaker sentences, removes empty text, and indexes segments.
"""
from __future__ import annotations

import re
from typing import List, Tuple
from app.models.orm import TranscriptSegment
from app.providers.base import ProviderTranscript

_UNMAPPED_SPEAKER_RE = re.compile(r"^(speaker|unknown)\s*\d*$", re.IGNORECASE)


def is_unmapped_speaker(speaker: str) -> bool:
    """Returns True if the speaker name is a generic unmapped label."""
    if not speaker or not speaker.strip():
        return True
    return bool(_UNMAPPED_SPEAKER_RE.match(speaker.strip()))


def normalize_transcript(
    transcript: ProviderTranscript,
    meeting_id: str = "",
) -> List[TranscriptSegment]:
    """
    Normalizes a ProviderTranscript into TranscriptSegment ORM models.
    
    Rules:
      - Merges consecutive sentences from the same speaker if time gap < 2.0 seconds.
      - Strips whitespace and drops empty sentences.
      - Maintains chronological order.
      - Assigns sequential idx starting at 0.
    """
    raw_sentences = transcript.sentences or []
    if not raw_sentences:
        return []

    # Sort strictly by start_time to preserve chronological flow
    sorted_sentences = sorted(raw_sentences, key=lambda s: s.start_time)

    merged: List[dict] = []
    for s in sorted_sentences:
        text = s.text.strip()
        if not text:
            continue

        speaker = s.speaker_name.strip() if s.speaker_name else "Unknown"

        if merged:
            last = merged[-1]
            gap = s.start_time - last["end_s"]
            # Merge condition: same speaker and gap under 2 seconds
            if last["speaker_raw"] == speaker and gap < 2.0:
                last["text"] = f"{last['text']} {text}"
                last["end_s"] = max(last["end_s"], s.end_time)
                continue

        merged.append({
            "speaker_raw": speaker,
            "text": text,
            "start_s": s.start_time,
            "end_s": max(s.end_time, s.start_time + 0.1),
        })

    segments: List[TranscriptSegment] = []
    for idx, item in enumerate(merged):
        segments.append(
            TranscriptSegment(
                meeting_id=meeting_id,
                idx=idx,
                speaker_raw=item["speaker_raw"],
                text=item["text"],
                start_s=item["start_s"],
                end_s=item["end_s"],
            )
        )

    return segments
