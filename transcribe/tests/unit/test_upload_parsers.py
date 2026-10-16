"""
Unit tests for upload parsers (PRD Section 15.4, U1-U6).
"""
import pytest
from app.providers.upload import parse_upload


def test_u1_txt_upload():
    content = b"Rahul: I will do task 1.\nPriya: I will do task 2."
    transcript = parse_upload(content, "sample.txt")
    assert len(transcript.sentences) == 2
    assert transcript.sentences[0].speaker_name == "Rahul"
    assert transcript.sentences[1].speaker_name == "Priya"


def test_u2_vtt_upload():
    content = b"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nRahul: Welcome everyone."
    transcript = parse_upload(content, "sample.vtt")
    assert len(transcript.sentences) == 1
    assert transcript.sentences[0].start_time == 1.0


def test_u3_json_upload():
    content = b'{"segments":[{"speaker":"Anita","text":"Let us start","start":0.0,"end":2.0}]}'
    transcript = parse_upload(content, "sample.json")
    assert len(transcript.sentences) == 1
    assert transcript.sentences[0].speaker_name == "Anita"


def test_u4_large_file_rejected():
    large_content = b"a" * (6 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds the 5 MB limit"):
        parse_upload(large_content, "large.txt")


def test_u5_binary_rejected():
    binary_content = b"\x80\x81\xff\xfe"
    with pytest.raises(ValueError, match="not valid UTF-8"):
        parse_upload(binary_content, "binary.txt")
