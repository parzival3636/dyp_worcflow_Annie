"""
Manual transcript file upload parser (.txt, .vtt, .srt, .json).
Converts uploaded transcripts into standard ProviderTranscript models.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional
from datetime import datetime, timezone

from app.providers.base import ProviderSentence, ProviderTranscript

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _parse_timestamp_s(ts_str: str) -> float:
    """Parses timestamps in HH:MM:SS.mmm or MM:SS.mmm to seconds."""
    ts_str = ts_str.replace(",", ".").strip()
    parts = ts_str.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    try:
        return float(ts_str)
    except ValueError:
        return 0.0


def parse_upload(content: bytes, filename: str, title: Optional[str] = None) -> ProviderTranscript:
    """
    Parses uploaded transcript files.
    Enforces 5 MB max limit and valid UTF-8 encoding.
    """
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size ({len(content)} bytes) exceeds the 5 MB limit.")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File content is not valid UTF-8 encoded text.")

    sentences: List[ProviderSentence] = []
    lower_fn = filename.lower()

    if lower_fn.endswith(".json"):
        try:
            data = json.loads(text)
        except Exception as e:
            raise ValueError(f"Invalid JSON transcript: {e}")

        raw_list = data.get("segments") or data.get("sentences") or []
        for i, item in enumerate(raw_list):
            speaker = item.get("speaker") or item.get("speaker_name") or "Unknown"
            s_text = item.get("text", "").strip()
            start = float(item.get("start") or item.get("start_time") or 0.0)
            end = float(item.get("end") or item.get("end_time") or start + 2.0)
            if s_text:
                sentences.append(
                    ProviderSentence(
                        index=i,
                        speaker_name=speaker,
                        text=s_text,
                        start_time=start,
                        end_time=end,
                    )
                )

    elif lower_fn.endswith(".vtt") or lower_fn.endswith(".srt"):
        # Match timestamp lines: e.g. 00:00:01.000 --> 00:00:03.500
        time_pattern = re.compile(r"(\d{1,2}:?\d{2}:\d{2}[\.,]\d{3})\s*-->\s*(\d{1,2}:?\d{2}:\d{2}[\.,]\d{3})")
        lines = text.splitlines()
        i = 0
        current_start = 0.0
        current_end = 0.0
        idx = 0

        while i < len(lines):
            line = lines[i].strip()
            m = time_pattern.search(line)
            if m:
                current_start = _parse_timestamp_s(m.group(1))
                current_end = _parse_timestamp_s(m.group(2))
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip() and not time_pattern.search(lines[i]):
                    text_lines.append(lines[i].strip())
                    i += 1
                full_text = " ".join(text_lines)
                if full_text:
                    speaker = "Unknown"
                    if ":" in full_text:
                        spk_part, rest = full_text.split(":", 1)
                        if len(spk_part.split()) <= 4:
                            speaker = spk_part.strip()
                            full_text = rest.strip()
                    sentences.append(
                        ProviderSentence(
                            index=idx,
                            speaker_name=speaker,
                            text=full_text,
                            start_time=current_start,
                            end_time=current_end,
                        )
                    )
                    idx += 1
            else:
                i += 1

    else:
        # Standard .txt parser (line format "Speaker: text" or timestamped "[00:01] Speaker: text")
        line_re = re.compile(r"^(?:\[(?P<time>[^\]]+)\]\s*)?(?:(?P<speaker>[A-Za-z0-9_\s]{2,40}):\s*)?(?P<text>.+)$")
        current_time = 0.0
        idx = 0
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            m = line_re.match(line)
            if m:
                s_text = m.group("text").strip()
                if not s_text:
                    continue
                speaker = (m.group("speaker") or "Unknown").strip()
                t_str = m.group("time")
                if t_str:
                    current_time = _parse_timestamp_s(t_str)
                sentences.append(
                    ProviderSentence(
                        index=idx,
                        speaker_name=speaker,
                        text=s_text,
                        start_time=current_time,
                        end_time=current_time + 2.5,
                    )
                )
                current_time += 2.5
                idx += 1

    total_duration = int(sentences[-1].end_time) if sentences else 0
    return ProviderTranscript(
        id=f"upload_{int(datetime.now(timezone.utc).timestamp())}",
        title=title or filename,
        date=datetime.now(timezone.utc).isoformat(),
        duration=total_duration,
        participants=list({s.speaker_name for s in sentences if s.speaker_name != "Unknown"}),
        speakers=[{"name": spk} for spk in set(s.speaker_name for s in sentences)],
        sentences=sentences,
    )
