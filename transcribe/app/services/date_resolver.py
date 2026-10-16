"""
Relative date resolution against meeting date and timezone.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
import dateutil.tz

from app.models.schemas import AmbiguityFlag

_VAGUE_PATTERNS = re.compile(r"\b(soon|asap|later|sometime|eventually|in the future)\b", re.IGNORECASE)
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_date(
    deadline_raw: Optional[str],
    meeting_dt: Optional[datetime],
    tz_name: str = "Asia/Kolkata",
) -> Tuple[Optional[date], Optional[AmbiguityFlag]]:
    """
    Resolves relative date expressions relative to meeting_dt.
    
    Returns (resolved_date, ambiguity_flag).
    """
    if not deadline_raw or not deadline_raw.strip():
        return None, AmbiguityFlag.NO_DEADLINE

    raw = deadline_raw.strip().lower()

    if _VAGUE_PATTERNS.search(raw) or "sometime next week" in raw:
        return None, AmbiguityFlag.VAGUE_DEADLINE

    base_date = (meeting_dt or datetime.now()).date()

    # EOD (End of day) -> meeting date
    if raw in ("eod", "end of day", "today", "by today"):
        return base_date, None

    # Tomorrow
    if "tomorrow" in raw:
        return base_date + timedelta(days=1), None

    # In X days
    m_days = re.search(r"in\s+(\d+|one|two|three|four|five)\s+days?", raw)
    if m_days:
        num_word = m_days.group(1)
        word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        d_val = word_to_num.get(num_word, int(num_word) if num_word.isdigit() else 1)
        return base_date + timedelta(days=d_val), None

    # End of the month
    if "end of the month" in raw or "end of month" in raw:
        _, last_day = calendar.monthrange(base_date.year, base_date.month)
        return date(base_date.year, base_date.month, last_day), None

    # Weekdays ("by Friday", "next Friday", etc.)
    for day_name, day_idx in _WEEKDAYS.items():
        if day_name in raw:
            is_next = "next" in raw
            current_day_idx = base_date.weekday()

            if is_next:
                # Next week's weekday
                days_ahead = (day_idx - current_day_idx) % 7
                if days_ahead == 0:
                    days_ahead = 7
                else:
                    days_ahead += 7
            else:
                # Same week or upcoming weekday
                # Rule: "by Friday" said on Friday means that same day
                days_ahead = (day_idx - current_day_idx) % 7

            return base_date + timedelta(days=days_ahead), None

    return None, AmbiguityFlag.VAGUE_DEADLINE
