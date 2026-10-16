"""
Unit tests for transcript normalizer (PRD Section 15.5, N1-N5).
"""
from app.providers.base import ProviderSentence, ProviderTranscript
from app.services.normalizer import normalize_transcript, is_unmapped_speaker


def test_n1_merge_consecutive_same_speaker_under_2s():
    t = ProviderTranscript(
        id="test",
        sentences=[
            ProviderSentence(index=0, speaker_name="Alice", text="First part.", start_time=1.0, end_time=2.0),
            ProviderSentence(index=1, speaker_name="Alice", text="Second part.", start_time=3.0, end_time=4.5),
        ],
    )
    segments = normalize_transcript(t)
    assert len(segments) == 1
    assert segments[0].text == "First part. Second part."
    assert segments[0].start_s == 1.0
    assert segments[0].end_s == 4.5


def test_n2_do_not_merge_gap_over_2s():
    t = ProviderTranscript(
        id="test",
        sentences=[
            ProviderSentence(index=0, speaker_name="Alice", text="First part.", start_time=1.0, end_time=2.0),
            ProviderSentence(index=1, speaker_name="Alice", text="Second part.", start_time=7.0, end_time=8.5),
        ],
    )
    segments = normalize_transcript(t)
    assert len(segments) == 2


def test_n3_empty_sentences_dropped():
    t = ProviderTranscript(
        id="test",
        sentences=[
            ProviderSentence(index=0, speaker_name="Alice", text="  ", start_time=1.0, end_time=2.0),
            ProviderSentence(index=1, speaker_name="Bob", text="Hello.", start_time=3.0, end_time=4.0),
        ],
    )
    segments = normalize_transcript(t)
    assert len(segments) == 1
    assert segments[0].speaker_raw == "Bob"


def test_n4_unmapped_speaker_check():
    assert is_unmapped_speaker("Speaker 2") is True
    assert is_unmapped_speaker("unknown 1") is True
    assert is_unmapped_speaker("Alice") is False


def test_n5_different_speakers_order_preserved():
    t = ProviderTranscript(
        id="test",
        sentences=[
            ProviderSentence(index=0, speaker_name="Alice", text="Hi", start_time=1.0, end_time=2.0),
            ProviderSentence(index=1, speaker_name="Bob", text="Hey", start_time=1.5, end_time=2.5),
        ],
    )
    segments = normalize_transcript(t)
    assert len(segments) == 2
    assert segments[0].speaker_raw == "Alice"
    assert segments[1].speaker_raw == "Bob"
