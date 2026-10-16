"""
Token-aware transcript chunking with overlap.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
from app.models.orm import TranscriptSegment


def estimate_tokens(text: str) -> int:
    """Estimates tokens using ~4 chars per token fallback."""
    return max(1, len(text) // 4)


@dataclass
class TranscriptChunk:
    chunk_index: int
    segments: List[TranscriptSegment]
    start_idx: int
    end_idx: int
    formatted_text: str
    token_count: int


def format_segment_line(seg: TranscriptSegment) -> str:
    m = int(seg.start_s // 60)
    s = int(seg.start_s % 60)
    time_str = f"{m:02d}:{s:02d}"
    return f"[{seg.idx} | {time_str}] {seg.speaker_raw}: {seg.text}"


def chunk_segments(
    segments: List[TranscriptSegment],
    chunk_size_tokens: int = 6000,
    overlap_tokens: int = 300,
) -> List[TranscriptChunk]:
    """
    Splits transcript segments into overlapping chunks.
    Ensures that a single segment is never split across chunks.
    """
    if not segments:
        return []

    chunks: List[TranscriptChunk] = []
    seg_lines = [format_segment_line(seg) for seg in segments]
    seg_tokens = [estimate_tokens(line) for line in seg_lines]

    i = 0
    chunk_idx = 0

    while i < len(segments):
      current_chunk_segs: List[TranscriptSegment] = []
      current_lines: List[str] = []
      current_tokens = 0
      start_idx = segments[i].idx
      chunk_start_pos = i

      while i < len(segments):
        seg = segments[i]
        tokens = seg_tokens[i]

        # If single segment exceeds chunk size, still emit it alone without truncation
        if not current_chunk_segs and tokens >= chunk_size_tokens:
          current_chunk_segs.append(seg)
          current_lines.append(seg_lines[i])
          current_tokens += tokens
          i += 1
          break

        if current_chunk_segs and (current_tokens + tokens > chunk_size_tokens):
          break

        current_chunk_segs.append(seg)
        current_lines.append(seg_lines[i])
        current_tokens += tokens
        i += 1

      end_idx = current_chunk_segs[-1].idx
      chunks.append(
          TranscriptChunk(
              chunk_index=chunk_idx,
              segments=current_chunk_segs,
              start_idx=start_idx,
              end_idx=end_idx,
              formatted_text="\n".join(current_lines),
              token_count=current_tokens,
          )
      )
      chunk_idx += 1

      if i >= len(segments):
        break

      # Overlap calculation within current chunk
      overlap_accum = 0
      overlap_count = 0
      for seg_tok in reversed(seg_tokens[chunk_start_pos:i]):
        if overlap_count > 0 and (overlap_accum + seg_tok > overlap_tokens):
          break
        overlap_accum += seg_tok
        overlap_count += 1
        if overlap_accum >= overlap_tokens:
          break

      # Next chunk must advance by at least 1 segment to prevent infinite loops
      advance = max(1, len(current_chunk_segs) - overlap_count)
      i = chunk_start_pos + advance

    return chunks
