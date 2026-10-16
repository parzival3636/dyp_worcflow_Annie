"""
Unit tests for chunker (PRD Section 15.5, C1-C3).
"""
from app.models.orm import TranscriptSegment
from app.services.chunker import chunk_segments


def test_c1_short_transcript_one_chunk():
    segs = [
        TranscriptSegment(idx=0, speaker_raw="A", text="Hello", start_s=0.0, end_s=1.0),
        TranscriptSegment(idx=1, speaker_raw="B", text="World", start_s=1.0, end_s=2.0),
    ]
    chunks = chunk_segments(segs, chunk_size_tokens=1000)
    assert len(chunks) == 1
    assert chunks[0].start_idx == 0
    assert chunks[0].end_idx == 1


def test_c2_multiple_chunks_with_overlap():
    segs = [
        TranscriptSegment(idx=i, speaker_raw="A", text="Line of speech " * 5, start_s=float(i), end_s=float(i+1))
        for i in range(25)
    ]
    # Chunk size accommodates multiple segments per chunk and provides overlap
    chunks = chunk_segments(segs, chunk_size_tokens=100, overlap_tokens=30)
    assert len(chunks) > 1
    # Check that overlap occurred (chunk 1 starts at or before chunk 0 ended)
    assert chunks[1].start_idx <= chunks[0].end_idx


def test_c3_single_segment_larger_than_chunk_size_not_truncated():
    segs = [
        TranscriptSegment(idx=0, speaker_raw="A", text="Very long speech " * 100, start_s=0.0, end_s=50.0),
    ]
    chunks = chunk_segments(segs, chunk_size_tokens=50)
    assert len(chunks) == 1
    assert chunks[0].segments[0].idx == 0
