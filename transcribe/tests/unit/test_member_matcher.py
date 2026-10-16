"""
Unit tests for member matcher (PRD Section 15.5, MM1-MM6).
"""
from app.integrations.members import ProjectMember
from app.models.schemas import AmbiguityFlag
from app.services.member_matcher import match_member_from_speaker_or_raw

MEMBERS = [
    ProjectMember(member_id="m1", full_name="Rahul Sharma", aliases=["kabs"]),
    ProjectMember(member_id="m2", full_name="Priya Patel", aliases=["pri"]),
    ProjectMember(member_id="m3", full_name="Anita Rao", aliases=["ani"]),
]


def test_mm1_exact_name():
    res = match_member_from_speaker_or_raw("Rahul Sharma", None, "", MEMBERS)
    assert res.member is not None
    assert res.member.member_id == "m1"
    assert res.confidence == 1.0


def test_mm2_first_name_single_match():
    res = match_member_from_speaker_or_raw("Priya", None, "", MEMBERS)
    assert res.member is not None
    assert res.member.member_id == "m2"


def test_mm3_tie_ambiguous():
    two_rahuls = [
        ProjectMember(member_id="m1", full_name="Rahul Sharma"),
        ProjectMember(member_id="m4", full_name="Rahul Verma"),
    ]
    res = match_member_from_speaker_or_raw("Rahul", None, "", two_rahuls)
    assert res.member is None
    assert res.flag == AmbiguityFlag.MULTIPLE_OWNERS


def test_mm4_fuzzy_match():
    res = match_member_from_speaker_or_raw("Rahull", None, "", MEMBERS)
    assert res.member is not None
    assert res.member.member_id == "m1"


def test_mm5_first_person_resolves_to_speaker():
    res = match_member_from_speaker_or_raw(None, "Priya Patel", "I'll do the auth integration", MEMBERS)
    assert res.member is not None
    assert res.member.member_id == "m2"


def test_mm6_pronouns_unresolved():
    res = match_member_from_speaker_or_raw("someone", "Rahul Sharma", "Someone should do this", MEMBERS)
    assert res.member is None
    assert res.flag == AmbiguityFlag.NO_OWNER
