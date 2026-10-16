from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, UniqueConstraint, Index
from sqlalchemy import JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB

# Use JSONB for Postgres and JSON fallback for SQLite
JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    idea: Optional[str] = None
    repo_full_name: Optional[str] = None
    repo_url: Optional[str] = None
    lead_member_id: Optional[int] = None
    telegram_group_id: Optional[int] = None
    status: str = Field(default="planning")  # planning | running | done
    starts_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    ends_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    last_polled_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))


class Member(SQLModel, table=True):
    __tablename__ = "member"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    name: Optional[str] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    github_login: Optional[str] = None
    skills: Optional[str] = None
    aliases: list = Field(default_factory=list, sa_type=JSON_TYPE)
    role: str = Field(default="member")  # lead | member
    invite_status: str = Field(default="pending")  # pending | accepted
    onboarding_state: Optional[str] = Field(default="new")  # new | awaiting_github | done
    active_task_id: Optional[int] = None
    awaiting_clarification: bool = Field(default=False)


class Block(SQLModel, table=True):
    __tablename__ = "block"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    name: Optional[str] = None
    total_effort: Optional[int] = None
    owner_member_id: Optional[int] = None
    oversize_flag: bool = Field(default=False)


class Task(SQLModel, table=True):
    __tablename__ = "task"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_task_project_key"),
        Index("ix_task_project_status", "project_id", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    key: str = Field(index=True)  # always 'T-<number>'
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: list = Field(default_factory=list, sa_type=JSON_TYPE)
    effort: Optional[int] = None
    status: str = Field(default="todo")  # todo | in_progress | blocked | claimed_done | needs_review | verified_done
    is_milestone: bool = Field(default=False)
    block_id: Optional[int] = None
    owner_member_id: Optional[int] = None
    deadline: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    started_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    completed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    progress: int = Field(default=0)
    risk: str = Field(default="ok")  # ok | at_risk | critical
    last_checkin_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    checkin_count: int = Field(default=0)


class TaskDep(SQLModel, table=True):
    __tablename__ = "task_dep"

    task_id: int = Field(foreign_key="task.id", primary_key=True, index=True)
    depends_on_task_id: int = Field(foreign_key="task.id", primary_key=True, index=True)
    kind: str = Field(default="hard")  # hard | handoff


class Message(SQLModel, table=True):
    __tablename__ = "message"
    __table_args__ = (
        Index("ix_message_member_created", "member_id", "created_at"),
        Index("ix_message_project_created", "project_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = None
    member_id: Optional[int] = None
    task_id: Optional[int] = None
    direction: str  # out | in
    text: Optional[str] = None
    parsed_json: Optional[dict] = Field(default=None, sa_type=JSON_TYPE)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    source: Optional[str] = Field(default="dm")  # dm | group
    chat_id: Optional[int] = None
    tg_message_id: Optional[int] = None
    reply_to_tg_message_id: Optional[int] = None
    processed: bool = Field(default=False)


class Blocker(SQLModel, table=True):
    __tablename__ = "blocker"
    __table_args__ = (
        Index("ix_blocker_task_status", "task_id", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    description: Optional[str] = None
    type: Optional[str] = None
    needed_from: Optional[str] = None
    routed_to_member_id: Optional[int] = None
    status: str = Field(default="open")  # open | routed | resolved
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    resolved_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))


class Contradiction(SQLModel, table=True):
    __tablename__ = "contradiction"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = None
    task_ids: list = Field(default_factory=list, sa_type=JSON_TYPE)
    member_ids: list = Field(default_factory=list, sa_type=JSON_TYPE)
    summary: Optional[str] = None
    status: str = Field(default="open")  # open | resolved
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    resolved_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    resolution: Optional[str] = None


class Verification(SQLModel, table=True):
    __tablename__ = "verification"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    verdict: Optional[str] = None  # verified | partial | no_evidence
    confidence: Optional[float] = None
    matched_shas: list = Field(default_factory=list, sa_type=JSON_TYPE)
    criteria_results: list = Field(default_factory=list, sa_type=JSON_TYPE)
    reason: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )


class CommitLog(SQLModel, table=True):
    __tablename__ = "commit_log"
    __table_args__ = (
        Index("ix_commit_log_project_committed", "project_id", "committed_at"),
    )

    sha: str = Field(primary_key=True)
    project_id: Optional[int] = None
    author_login: Optional[str] = None
    member_id: Optional[int] = None
    message: Optional[str] = None
    files: list = Field(default_factory=list, sa_type=JSON_TYPE)
    additions: Optional[int] = None
    deletions: Optional[int] = None
    committed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    task_id: Optional[int] = None


class Event(SQLModel, table=True):
    __tablename__ = "event"
    __table_args__ = (
        Index("ix_event_project_ts_desc", "project_id", "ts"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = None
    ts: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    actor_member_id: Optional[int] = None
    type: str  # one of the 18 event types
    task_id: Optional[int] = None
    payload: Optional[dict] = Field(default=None, sa_type=JSON_TYPE)
