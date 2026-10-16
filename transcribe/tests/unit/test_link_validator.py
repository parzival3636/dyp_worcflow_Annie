"""
Unit tests for meeting link validator (PRD Section 15.1, L1-L13).
"""
import pytest
from app.models.orm import PlatformEnum
from app.services.link_validator import validate_and_normalize, InvalidMeetingLink


def test_l1_google_meet_valid():
    res = validate_and_normalize("https://meet.google.com/abc-defg-hij")
    assert res.platform == PlatformEnum.GOOGLE_MEET
    assert res.url == "https://meet.google.com/abc-defg-hij"


def test_l2_google_meet_normalized_params():
    res = validate_and_normalize("  https://meet.google.com/abc-defg-hij?authuser=0&utm_source=x  ")
    assert res.platform == PlatformEnum.GOOGLE_MEET
    assert res.url == "https://meet.google.com/abc-defg-hij"


def test_l3_forced_https():
    res = validate_and_normalize("http://meet.google.com/abc-defg-hij")
    assert res.platform == PlatformEnum.GOOGLE_MEET
    assert res.url == "https://meet.google.com/abc-defg-hij"


def test_l4_no_scheme_added():
    res = validate_and_normalize("MEET.GOOGLE.COM/abc-defg-hij")
    assert res.platform == PlatformEnum.GOOGLE_MEET
    assert res.url == "https://meet.google.com/abc-defg-hij"


def test_l5_bad_code_format():
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize("https://meet.google.com/abcdefghij")


def test_l6_zoom_valid_pwd_kept():
    res = validate_and_normalize("https://us02web.zoom.us/j/81234567890?pwd=AbC123")
    assert res.platform == PlatformEnum.ZOOM
    assert "pwd=AbC123" in res.url
    assert "https://us02web.zoom.us/j/81234567890" in res.url


def test_l7_teams_valid():
    res = validate_and_normalize("https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc/0?context=123")
    assert res.platform == PlatformEnum.TEAMS


def test_l8_evil_path_spoof():
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize("https://evil.com/meet.google.com/abc-defg-hij")


def test_l9_host_spoof():
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize("https://meet.google.com.evil.com/abc-defg-hij")


def test_l10_javascript_scheme():
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize("javascript:alert(1)")


def test_l11_empty_string():
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize("   ")


def test_l12_too_long():
    long_link = "https://meet.google.com/abc-defg-hij?" + "a" * 2500
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize(long_link)


def test_l13_whitespace_inside():
    with pytest.raises(InvalidMeetingLink):
        validate_and_normalize("https://meet.google.com/abc-defg-hij extra text")
