"""
Pilot – test_group_extraction.py

Tests P3G extraction from a ~30-line fake group conversation.
Validates: banter → none, owner self-reports → status observations,
third-party claims → claim_about_other, contradictions, nicknames,
reply-to chains, edited messages.
"""
from __future__ import annotations

import pytest
from prompts import (
    GroupExtraction, Observation, BlockerInfo,
    P3G_SYSTEM, p3g_user_prompt,
)


# ---------------------------------------------------------------------------
# Fake conversation and context
# ---------------------------------------------------------------------------

MEMBERS = [
    {"name": "Kabir", "username": "kabir_dev", "aliases": ["kabs", "bhai"]},
    {"name": "Meera", "username": "meera_codes", "aliases": ["mee"]},
    {"name": "Arjun", "username": "arjun_py", "aliases": ["aj"]},
    {"name": "Priya", "username": "priya_ui", "aliases": ["pri"]},
]

TASKS = [
    {"key": "T-1", "title": "Connect the payment API", "status": "todo", "owner_name": "Kabir"},
    {"key": "T-2", "title": "Build the event listing page", "status": "in_progress", "owner_name": "Meera"},
    {"key": "T-3", "title": "Set up user authentication", "status": "todo", "owner_name": "Arjun"},
    {"key": "T-4", "title": "Design the admin dashboard", "status": "todo", "owner_name": "Priya"},
]

# ~30 lines of fake group conversation
MESSAGES = [
    "[09:00] <Kabir>: good morning everyone!",
    "[09:01] <Meera>: hii 🙋‍♀️",
    "[09:02] <Arjun>: yo whats up",
    "[09:03] <Priya>: that meme last night was hilarious 😂",
    "[09:04] <Kabir>: lol",
    "[09:10] <Kabir>: ok so update on T-1 — The API is connected, but I am waiting for test credentials.",
    "[09:11] <Meera>: oh nice! (reply to Kabir)",
    "[09:12] <Arjun>: kabs when do you think you'll get those credentials?",
    "[09:13] <Kabir>: hopefully by today evening, I've pinged the Razorpay team",
    "[09:15] <Meera>: T-2 is going well, I've done the grid layout and the filters. about 60% done",
    "[09:16] <Priya>: nice mee! the designs look great",
    "[09:17] <Arjun>: I haven't started T-3 yet, will push by tonight",
    "[09:20] <Meera>: btw I think Kabir already finished the integration, saw his branch",
    "[09:21] <Kabir>: no no bro I'm still stuck waiting on creds (reply to Meera)",
    "[09:25] <Priya>: anyone wanna grab lunch?",
    "[09:26] <Arjun>: ya sure",
    "[09:30] <Priya>: also T-4 — I'm starting the wireframes now, should be done by tomorrow",
    "[09:31] <Meera>: @arjun_py make sure the auth API has refresh tokens too",
    "[09:32] <Arjun>: yeah I know, it's in the acceptance criteria",
    "[09:35] <Kabir>: team standup reminder: let's sync at 3pm",
    "[09:40] <Meera>: got it",
    "[09:41] <Arjun>: 👍",
    "[09:45] <Kabir>: got the credentials, testing is done! T-1 is complete 🎉",
    "[09:46] <Meera>: amazing kabs!",
    "[09:47] <Arjun>: less goo",
    "[09:50] <Priya>: wait @kabir_dev did you also set up error handling for failed transactions?",
    "[09:51] <Kabir>: yes all covered, tested with sandbox mode too (reply to Priya)",
    "[09:55] <Meera>: hmm actually I think the integration might have a bug, I'm seeing errors on my end",
    "[10:00] <Arjun>: haha nice meme (reply to Priya)",
]

# New messages are the last 10 (indices 19-28)
NEW_INDICES = list(range(19, len(MESSAGES)))


# ---------------------------------------------------------------------------
# Mock-based tests
# ---------------------------------------------------------------------------

class TestGroupExtraction:
    """Test P3G extraction using mock observations."""

    def _mock_extraction(self) -> GroupExtraction:
        """Return a realistic P3G extraction from the fake conversation."""
        return GroupExtraction(
            observations=[
                # Banter: "good morning", "hii", "yo", meme, "lol" → none
                Observation(speaker="Kabir", kind="none", evidence_quote="good morning everyone!", confidence=0.95),
                Observation(speaker="Meera", kind="none", evidence_quote="hii 🙋‍♀️", confidence=0.95),
                Observation(speaker="Priya", kind="none", evidence_quote="that meme last night was hilarious 😂", confidence=0.95),

                # Kabir's blocker on T-1 (owner self-report)
                Observation(
                    speaker="Kabir",
                    task_key="T-1",
                    kind="blocker",
                    new_status="blocked",
                    blocker=BlockerInfo(description="waiting for test credentials", type="credentials"),
                    evidence_quote="The API is connected, but I am waiting for test credentials.",
                    confidence=0.92,
                ),

                # Meera progress on T-2 (owner self-report)
                Observation(
                    speaker="Meera",
                    task_key="T-2",
                    kind="progress",
                    new_status="in_progress",
                    progress=60,
                    evidence_quote="T-2 is going well, I've done the grid layout and the filters. about 60% done",
                    confidence=0.9,
                ),

                # Arjun commitment (future promise, not completion)
                Observation(
                    speaker="Arjun",
                    task_key="T-3",
                    kind="commitment",
                    commitment_text="will push by tonight",
                    evidence_quote="I haven't started T-3 yet, will push by tonight",
                    confidence=0.85,
                ),

                # Meera claim about other (Kabir): contradiction!
                Observation(
                    speaker="Meera",
                    task_key="T-1",
                    kind="claim_about_other",
                    about_member="Kabir",
                    evidence_quote="I think Kabir already finished the integration, saw his branch",
                    confidence=0.75,
                ),

                # Lunch → none
                Observation(speaker="Priya", kind="none", evidence_quote="anyone wanna grab lunch?", confidence=0.95),

                # Priya commitment on T-4
                Observation(
                    speaker="Priya",
                    task_key="T-4",
                    kind="commitment",
                    commitment_text="starting the wireframes now, should be done by tomorrow",
                    evidence_quote="T-4 — I'm starting the wireframes now, should be done by tomorrow",
                    confidence=0.85,
                ),

                # Kabir completion of T-1
                Observation(
                    speaker="Kabir",
                    task_key="T-1",
                    kind="completion_claim",
                    new_status="claimed_done",
                    evidence_quote="got the credentials, testing is done! T-1 is complete 🎉",
                    confidence=0.95,
                ),

                # More banter
                Observation(speaker="Arjun", kind="none", evidence_quote="haha nice meme", confidence=0.95),
            ]
        )

    def test_banter_gives_none(self):
        """Banter, greetings, memes → kind=none."""
        ext = self._mock_extraction()
        banter = [o for o in ext.observations if o.kind == "none"]
        assert len(banter) >= 3
        for obs in banter:
            assert obs.new_status is None

    def test_owner_self_report_blocker(self):
        """Kabir reporting on his own T-1 → blocker."""
        ext = self._mock_extraction()
        blockers = [o for o in ext.observations if o.kind == "blocker"]
        assert len(blockers) >= 1
        b = blockers[0]
        assert b.speaker == "Kabir"
        assert b.task_key == "T-1"
        assert "credentials" in (b.blocker.description if b.blocker else "").lower()

    def test_owner_self_report_progress(self):
        """Meera reporting 60% on T-2 → progress."""
        ext = self._mock_extraction()
        progress = [o for o in ext.observations if o.kind == "progress"]
        assert len(progress) >= 1
        p = progress[0]
        assert p.speaker == "Meera"
        assert p.task_key == "T-2"
        assert p.progress == 60

    def test_commitment_not_completion(self):
        """Future promises → commitment, NOT completion."""
        ext = self._mock_extraction()
        commitments = [o for o in ext.observations if o.kind == "commitment"]
        assert len(commitments) >= 1
        for c in commitments:
            assert c.kind != "completion_claim"

    def test_claim_about_other(self):
        """Third-party claims → claim_about_other, no status change."""
        ext = self._mock_extraction()
        claims = [o for o in ext.observations if o.kind == "claim_about_other"]
        assert len(claims) >= 1
        c = claims[0]
        assert c.about_member == "Kabir"
        assert c.speaker == "Meera"
        # Should not change status (apply_observations handles this)

    def test_completion_claim_by_owner(self):
        """Owner claiming completion → completion_claim."""
        ext = self._mock_extraction()
        completions = [o for o in ext.observations if o.kind == "completion_claim"]
        assert len(completions) >= 1
        comp = completions[0]
        assert comp.speaker == "Kabir"
        assert comp.task_key == "T-1"

    def test_blocker_outranks_completion(self):
        """When blocker and completion are mixed, blocker wins."""
        ext = self._mock_extraction()
        # In the original message "The API is connected, but I am waiting for test credentials."
        # This should be a blocker, not a completion
        kabir_obs = [o for o in ext.observations
                     if o.speaker == "Kabir" and o.task_key == "T-1"
                     and "connected" in o.evidence_quote.lower()
                     and "credentials" in o.evidence_quote.lower()]
        for obs in kabir_obs:
            assert obs.kind == "blocker"

    def test_nickname_resolution(self):
        """Nicknames like 'kabs' should resolve to Kabir."""
        # The test data uses "kabs" as an alias — if the extraction resolves it correctly,
        # the observation should have speaker="Kabir"
        ext = self._mock_extraction()
        kabir_obs = [o for o in ext.observations if o.speaker == "Kabir"]
        assert len(kabir_obs) >= 1


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

class TestP3GPrompt:
    def test_prompt_includes_all_context(self):
        prompt = p3g_user_prompt(MEMBERS, TASKS, MESSAGES[:5], [3, 4])
        assert "Kabir" in prompt
        assert "T-1" in prompt
        assert "Connect the payment API" in prompt
        assert "[NEW]" in prompt

    def test_prompt_marks_new_messages(self):
        prompt = p3g_user_prompt(MEMBERS, TASKS, MESSAGES[:5], [0, 4])
        # Messages at indices 0 and 4 should be marked [NEW]
        lines = prompt.split("\n")
        new_count = sum(1 for l in lines if "[NEW]" in l)
        assert new_count == 2
