"""
Unit tests for date resolver (PRD Section 15.5, D1-D7).
"""
from datetime import date, datetime
from app.models.schemas import AmbiguityFlag
from app.services.date_resolver import resolve_date


def test_d1_tomorrow():
    meeting_dt = datetime(2026, 3, 10, 10, 0)
    d, flag = resolve_date("tomorrow", meeting_dt)
    assert d == date(2026, 3, 11)
    assert flag is None


def test_d2_by_friday_from_monday():
    # 2026-03-09 is Monday, Friday is 2026-03-13
    meeting_dt = datetime(2026, 3, 9, 10, 0)
    d, flag = resolve_date("by Friday", meeting_dt)
    assert d == date(2026, 3, 13)
    assert flag is None


def test_d3_next_friday():
    # 2026-03-09 is Monday, Next Friday is 2026-03-20
    meeting_dt = datetime(2026, 3, 9, 10, 0)
    d, flag = resolve_date("next Friday", meeting_dt)
    assert d == date(2026, 3, 20)
    assert flag is None


def test_d4_end_of_the_month():
    meeting_dt = datetime(2026, 3, 10, 10, 0)
    d, flag = resolve_date("end of the month", meeting_dt)
    assert d == date(2026, 3, 31)
    assert flag is None


def test_d5_vague_deadlines():
    for word in ["ASAP", "soon", "sometime next week", "later"]:
        d, flag = resolve_date(word, datetime(2026, 3, 10))
        assert d is None
        assert flag == AmbiguityFlag.VAGUE_DEADLINE


def test_d6_eod():
    meeting_dt = datetime(2026, 3, 10, 15, 0)
    d, flag = resolve_date("EOD", meeting_dt)
    assert d == date(2026, 3, 10)
    assert flag is None


def test_d7_past_meeting_date_relative_resolution():
    meeting_dt = datetime(2020, 1, 15, 10, 0)
    d, flag = resolve_date("tomorrow", meeting_dt)
    assert d == date(2020, 1, 16)
