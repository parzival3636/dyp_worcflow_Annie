"""
Pilot – SQLModel table definitions.

Column / table names match schema.sql exactly.
Dynamic multi-tenant, authenticated schema for Supabase Postgres.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlmodel import Column, Field, SQLModel
from sqlalchemy import BigInteger, Text, UniqueConstraint, JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB

JSONB_COMPAT = JSONB().with_variant(JSON(), "sqlite")


# ---------------------------------------------------------------------------
# user
# ---------------------------------------------------------------------------
class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column(Text, unique=True, index=True, nullable=False))
    password_hash: str = Field(sa_column=Column(Text, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    role: str = Field(default="leader")  # leader | guide | member
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


# ---------------------------------------------------------------------------
# invite
# ---------------------------------------------------------------------------
class Invite(SQLModel, table=True):
    __tablename__ = "invite"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    email: str = Field(sa_column=Column(Text, nullable=False, index=True))
    role: str = Field(default="member")  # leader | guide | member
    token: str = Field(sa_column=Column(Text, unique=True, index=True, nullable=False))
    status: str = Field(default="pending")  # pending | accepted | revoked
    invited_by_user_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------
class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    idea: Optional[str] = None
    description: Optional[str] = None
    functional_requirements: Optional[str] = None
    non_functional_requirements: Optional[str] = None
    constraints: Optional[str] = None

    repo_full_name: Optional[str] = None
    repo_url: Optional[str] = None

    leader_user_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    lead_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    telegram_group_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    telegram_chat_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    telegram_status: str = Field(default="disconnected")  # disconnected | connecting | connected

    status: str = Field(default="planning")  # planning | running | done
    plan_status: str = Field(default="draft")  # draft | generated | balanced | active
    provisioning: Any = Field(default={}, sa_column=Column(JSONB_COMPAT, server_default="'{}'"))

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    last_polled_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )


# ---------------------------------------------------------------------------
# member
# ---------------------------------------------------------------------------
class Member(SQLModel, table=True):
    __tablename__ = "member"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    user_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    name: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    telegram_username: Optional[str] = None
    github_login: Optional[str] = None
    github_invite_status: str = Field(default="none")  # none | pending | accepted
    skills: Optional[str] = None

    aliases: Any = Field(default=[], sa_column=Column(JSONB_COMPAT, server_default="'[]'"))

    role: str = Field(default="member")           # lead | member | guide
    invite_status: str = Field(default="pending")  # pending | accepted
    onboarding_state: str = Field(default="new")  # new | awaiting_github | done

    active_task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    awaiting_clarification: bool = Field(default=False)


# ---------------------------------------------------------------------------
# block
# ---------------------------------------------------------------------------
class Block(SQLModel, table=True):
    __tablename__ = "block"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    name: Optional[str] = None
    total_effort: Optional[int] = None
    owner_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    oversize_flag: bool = Field(default=False)


# ---------------------------------------------------------------------------
# task
# ---------------------------------------------------------------------------
class Task(SQLModel, table=True):
    __tablename__ = "task"
    __table_args__ = (UniqueConstraint("project_id", "key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    key: str = Field(sa_column=Column(Text, nullable=False))  # T-<number>
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Any = Field(default=[], sa_column=Column(JSONB_COMPAT, server_default="'[]'"))
    effort: Optional[int] = None
    status: str = Field(default="todo")  # todo | in_progress | claimed_done | verified_done | blocked
    is_milestone: bool = Field(default=False)
    block_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    owner_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = Field(default=0)
    risk: str = Field(default="ok")
    tag: Optional[str] = Field(default=None)  # FR | NFR | CORE | INFRA
    last_checkin_at: Optional[datetime] = None
    checkin_count: int = Field(default=0)


# ---------------------------------------------------------------------------
# task_dep
# ---------------------------------------------------------------------------
class TaskDep(SQLModel, table=True):
    __tablename__ = "task_dep"

    task_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    depends_on_task_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    kind: str = Field(default="hard")  # hard | handoff


# ---------------------------------------------------------------------------
# message
# ---------------------------------------------------------------------------
class Message(SQLModel, table=True):
    __tablename__ = "message"
    __table_args__ = (UniqueConstraint("chat_id", "tg_message_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    direction: str = Field(sa_column=Column(Text, nullable=False))  # out | in
    text: Optional[str] = None
    intent: Optional[str] = None  # progress | blocker | question | handoff | off_topic
    parsed_json: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
    created_at: Optional[datetime] = Field(default=None)
    source: str = Field(default="dm")   # dm | group
    chat_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    tg_message_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    reply_to_tg_message_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    processed: bool = Field(default=False)


# ---------------------------------------------------------------------------
# blocker
# ---------------------------------------------------------------------------
class Blocker(SQLModel, table=True):
    __tablename__ = "blocker"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    description: Optional[str] = None
    type: Optional[str] = None
    needed_from: Optional[str] = None
    routed_to_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    status: str = Field(default="open")  # open | routed | resolved
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# contradiction
# ---------------------------------------------------------------------------
class Contradiction(SQLModel, table=True):
    __tablename__ = "contradiction"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    task_ids: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
    member_ids: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
    summary: Optional[str] = None
    status: str = Field(default="open")
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
class Verification(SQLModel, table=True):
    __tablename__ = "verification"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    claimed_by_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    claim_message_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    verdict: Optional[str] = None  # verified | rejected | inconclusive
    confidence: Optional[float] = None
    matched_shas: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
    criteria_results: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# commit_log
# ---------------------------------------------------------------------------
class CommitLog(SQLModel, table=True):
    __tablename__ = "commit_log"

    sha: str = Field(sa_column=Column(Text, primary_key=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    author_login: Optional[str] = None
    member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    message: Optional[str] = None
    files: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
    additions: Optional[int] = None
    deletions: Optional[int] = None
    committed_at: Optional[datetime] = None
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))


# ---------------------------------------------------------------------------
# event
# ---------------------------------------------------------------------------
class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    ts: Optional[datetime] = None
    actor_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    type: str = Field(sa_column=Column(Text, nullable=False))
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    payload: Any = Field(default=None, sa_column=Column(JSONB_COMPAT))
