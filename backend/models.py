"""
Pilot – SQLModel table definitions.

Column / table names match schema.sql exactly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from sqlmodel import Column, Field, SQLModel
from sqlalchemy import BigInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------
class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    code: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    idea: Optional[str] = None

    repo_full_name: Optional[str] = None
    repo_url: Optional[str] = None

    lead_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    telegram_group_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))

    status: str = Field(default="planning")  # planning | running | done

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    last_polled_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# member
# ---------------------------------------------------------------------------
class Member(SQLModel, table=True):
    __tablename__ = "member"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    name: Optional[str] = None
    telegram_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    telegram_username: Optional[str] = None
    github_login: Optional[str] = None
    skills: Optional[str] = None

    aliases: Any = Field(default=[], sa_column=Column(JSONB, server_default="'[]'"))

    role: str = Field(default="member")           # lead | member
    invite_status: str = Field(default="pending")
    onboarding_state: str = Field(default="new")  # new | awaiting_github | done

    active_task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    awaiting_clarification: bool = Field(default=False)


# ---------------------------------------------------------------------------
# block
# ---------------------------------------------------------------------------
class Block(SQLModel, table=True):
    __tablename__ = "block"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
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

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    key: str = Field(sa_column=Column(Text, nullable=False))  # T-<number>
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Any = Field(default=[], sa_column=Column(JSONB, server_default="'[]'"))
    effort: Optional[int] = None
    status: str = Field(default="todo")
    is_milestone: bool = Field(default=False)
    block_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    owner_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = Field(default=0)
    risk: str = Field(default="ok")
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

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    direction: str = Field(sa_column=Column(Text, nullable=False))  # out | in
    text: Optional[str] = None
    parsed_json: Any = Field(default=None, sa_column=Column(JSONB))
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

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
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

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    task_ids: Any = Field(default=None, sa_column=Column(JSONB))
    member_ids: Any = Field(default=None, sa_column=Column(JSONB))
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

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    matched_shas: Any = Field(default=None, sa_column=Column(JSONB))
    criteria_results: Any = Field(default=None, sa_column=Column(JSONB))
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# commit_log
# ---------------------------------------------------------------------------
class CommitLog(SQLModel, table=True):
    __tablename__ = "commit_log"

    sha: str = Field(sa_column=Column(Text, primary_key=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    author_login: Optional[str] = None
    member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    message: Optional[str] = None
    files: Any = Field(default=None, sa_column=Column(JSONB))
    additions: Optional[int] = None
    deletions: Optional[int] = None
    committed_at: Optional[datetime] = None
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))


# ---------------------------------------------------------------------------
# event
# ---------------------------------------------------------------------------
class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    project_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    ts: Optional[datetime] = None
    actor_member_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    type: str = Field(sa_column=Column(Text, nullable=False))
    task_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    payload: Any = Field(default=None, sa_column=Column(JSONB))
