"""
Member matching logic for resolving raw spoken names to project members.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from rapidfuzz import fuzz

from app.integrations.members import ProjectMember
from app.models.schemas import AmbiguityFlag

_FIRST_PERSON_PATTERN = re.compile(r"\b(i'll|i will|i can|let me|i'm going to|i am going to)\b", re.IGNORECASE)
_NON_OWNER_PRONOUNS = re.compile(r"\b(you|someone|anyone|we|somebody|anybody)\b", re.IGNORECASE)


@dataclass
class MatchResult:
    member: Optional[ProjectMember] = None
    confidence: float = 0.0
    flag: Optional[AmbiguityFlag] = None


def match_member_from_speaker_or_raw(
    owner_raw: Optional[str],
    speaker_raw: Optional[str],
    evidence: str,
    members: List[ProjectMember],
) -> MatchResult:
    """
    Resolves member identity following PRD Section 4.6:
    1. First-person rule: 'I'll do it' resolves to the speaker of that segment.
    2. 'You do X' / 'Someone should' does NOT resolve to anyone.
    3. Matching order: exact full name, alias, first-name match, fuzzy (>= 0.85).
    4. On ties, flag MULTIPLE_OWNERS or UNKNOWN_SPEAKER. Never guess.
    """
    if not members:
        return MatchResult(member=None, flag=AmbiguityFlag.UNKNOWN_SPEAKER if owner_raw else AmbiguityFlag.NO_OWNER)

    # First-person check
    if evidence and _FIRST_PERSON_PATTERN.search(evidence):
        if speaker_raw:
            owner_raw = speaker_raw

    # Pronoun non-owner check
    if owner_raw and _NON_OWNER_PRONOUNS.search(owner_raw.strip().lower()):
        return MatchResult(member=None, flag=AmbiguityFlag.NO_OWNER)

    if not owner_raw or not owner_raw.strip():
        return MatchResult(member=None, flag=AmbiguityFlag.NO_OWNER)

    name_query = owner_raw.strip().lower()

    # 1. Exact match on full name
    exact_matches = [m for m in members if m.full_name.lower() == name_query]
    if len(exact_matches) == 1:
        return MatchResult(member=exact_matches[0], confidence=1.0)
    elif len(exact_matches) > 1:
        return MatchResult(member=None, flag=AmbiguityFlag.MULTIPLE_OWNERS)

    # 2. Exact match on aliases
    alias_matches = [m for m in members if any(a.lower() == name_query for a in m.aliases)]
    if len(alias_matches) == 1:
        return MatchResult(member=alias_matches[0], confidence=0.95)
    elif len(alias_matches) > 1:
        return MatchResult(member=None, flag=AmbiguityFlag.MULTIPLE_OWNERS)

    # 3. First-name match
    first_name_matches = [
        m for m in members if m.full_name.split()[0].lower() == name_query
    ]
    if len(first_name_matches) == 1:
        return MatchResult(member=first_name_matches[0], confidence=0.90)
    elif len(first_name_matches) > 1:
        return MatchResult(member=None, flag=AmbiguityFlag.MULTIPLE_OWNERS)

    # 4. Fuzzy match >= 0.85
    scored: List[Tuple[ProjectMember, float]] = []
    for m in members:
        score_full = fuzz.ratio(name_query, m.full_name.lower()) / 100.0
        score_first = fuzz.ratio(name_query, m.full_name.split()[0].lower()) / 100.0
        score_alias = max([fuzz.ratio(name_query, a.lower()) / 100.0 for a in m.aliases] or [0.0])
        best_score = max(score_full, score_first, score_alias)
        if best_score >= 0.85:
            scored.append((m, best_score))

    if not scored:
        return MatchResult(member=None, flag=AmbiguityFlag.UNKNOWN_SPEAKER)

    # Sort descending by score
    scored.sort(key=lambda x: x[1], reverse=True)
    if len(scored) > 1 and abs(scored[0][1] - scored[1][1]) < 0.05:
        # Tie
        return MatchResult(member=None, flag=AmbiguityFlag.MULTIPLE_OWNERS)

    return MatchResult(member=scored[0][0], confidence=scored[0][1])
