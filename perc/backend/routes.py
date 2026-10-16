from datetime import datetime, timezone
from typing import Optional, Any
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select, desc

from backend.db import get_session
from backend.models import (
    Project,
    Member,
    Block,
    Task,
    TaskDep,
    Blocker,
    Contradiction,
    Verification,
    CommitLog,
    Event,
)
from backend.events import add_event
from backend.state import transition_task, IllegalTransition
from backend.llm import PlanGenerationError
from backend.planner import (
    generate_plan,
    bundle,
    assign,
    confirm_assignment,
    compute_deadlines,
    propose_split,
    apply_split,
)

router = APIRouter(prefix="/api", tags=["Pilot API"])

PALETTE = [
    "#2563eb",  # blue
    "#7c3aed",  # violet
    "#db2777",  # pink
    "#ea580c",  # orange
    "#16a34a",  # green
    "#0891b2",  # cyan
    "#4f46e5",  # indigo
    "#ca8a04",  # amber
]


# ---------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------

class CreateProjectRequest(BaseModel):
    code: str
    name: str
    idea: Optional[str] = None
    repo_url: Optional[str] = None
    lead_name: Optional[str] = "Lead"


class PlanRequest(BaseModel):
    idea: Optional[str] = None
    team_size: int = 4
    skills: list[str] = Field(default_factory=list)
    duration_hours: int = 20


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    effort: int = 2
    acceptance_criteria: list[str] = Field(default_factory=list)
    depends_on_keys: list[str] = Field(default_factory=list)
    is_milestone: bool = False


class TaskPatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    effort: Optional[int] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    owner_member_id: Optional[int] = None
    acceptance_criteria: Optional[list[str]] = None
    depends_on_keys: Optional[list[str]] = None


class AskRequest(BaseModel):
    question: str


# ---------------------------------------------------------
# Projects Endpoints
# ---------------------------------------------------------

@router.get("/projects")
def list_projects():
    with get_session() as session:
        projects = session.exec(select(Project).order_by(desc(Project.id))).all()
        return projects


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(req: CreateProjectRequest):
    with get_session() as session:
        existing = session.exec(select(Project).where(Project.code == req.code)).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Project code '{req.code}' already exists", "code": "PROJECT_EXISTS"},
            )

        now = datetime.now(timezone.utc)
        project = Project(
            code=req.code,
            name=req.name,
            idea=req.idea,
            repo_url=req.repo_url,
            status="planning",
            starts_at=now,
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Create default lead member
        lead = Member(
            project_id=project.id,
            name=req.lead_name,
            role="lead",
            invite_status="accepted",
        )
        session.add(lead)
        session.commit()
        session.refresh(lead)

        project.lead_member_id = lead.id
        session.add(project)

        add_event(
            session=session,
            project_id=project.id,
            type="project_created",
            actor_member_id=lead.id,
            payload={"code": project.code, "name": project.name},
        )
        session.commit()
        return project


@router.get("/projects/{code}")
def get_project_metadata(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )
        return project


def get_mock_snapshot(code: str) -> dict[str, Any]:
    return {
        "project": {
            "code": code,
            "name": "Pilot: Autonomous AI Project Coordinator",
            "status": "running",
            "repo_url": "https://github.com/pilot-team/pilot",
            "starts_at": "2026-10-16T10:00:00Z",
            "ends_at": "2026-10-16T18:00:00Z",
        },
        "members": [
            {"id": 1, "name": "Meera", "role": "lead", "github_login": "meera-lead", "invite_status": "accepted", "color": PALETTE[1 % len(PALETTE)]},
            {"id": 2, "name": "Kabir", "role": "member", "github_login": "kabir-dev", "invite_status": "accepted", "color": PALETTE[2 % len(PALETTE)]},
            {"id": 3, "name": "Aarav", "role": "member", "github_login": "aarav-bot", "invite_status": "accepted", "color": PALETTE[3 % len(PALETTE)]},
            {"id": 4, "name": "Diya", "role": "member", "github_login": "diya-qa", "invite_status": "accepted", "color": PALETTE[4 % len(PALETTE)]},
        ],
        "blocks": [
            {"id": 1, "name": "Core & Database Spine", "owner_member_id": 1, "total_effort": 12, "oversize_flag": False},
            {"id": 2, "name": "Backend Integrations & Brain", "owner_member_id": 2, "total_effort": 18, "oversize_flag": True},
            {"id": 3, "name": "Telegram Bot & Check-in Loop", "owner_member_id": 3, "total_effort": 10, "oversize_flag": False},
            {"id": 4, "name": "GitHub Verification & Stats", "owner_member_id": 4, "total_effort": 8, "oversize_flag": False},
        ],
        "tasks": [
            {"key": "T-1", "title": "Repo Setup & Project Skeleton", "status": "verified_done", "owner_member_id": 1, "block_id": 1, "deadline": "2026-10-16T11:00:00Z", "progress": 100, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Initial directory structure created", "CI configuration added"], "description": "Initialize repository structure and base configurations.", "verification": {"verdict": "verified", "confidence": 0.95, "reason": "Files and commits verified in repository"}, "blocker": None},
            {"key": "T-2", "title": "Database Schema & Models", "status": "verified_done", "owner_member_id": 1, "block_id": 1, "deadline": "2026-10-16T12:00:00Z", "progress": 100, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["All SQLModel models created", "Indexes specified"], "description": "Create Postgres models and database connection pool.", "verification": {"verdict": "verified", "confidence": 0.92, "reason": "Schema created and checked"}, "blocker": None},
            {"key": "T-3", "title": "FastAPI Base Routes & Health Check", "status": "verified_done", "owner_member_id": 1, "block_id": 1, "deadline": "2026-10-16T12:30:00Z", "progress": 100, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["GET /api/health functional", "CORS configured"], "description": "Implement core REST API foundations and error handlers.", "verification": {"verdict": "verified", "confidence": 0.90, "reason": "Health endpoint tested and functional"}, "blocker": None},
            {"key": "T-4", "title": "Telegram Bot Initialization & Webhook", "status": "in_progress", "owner_member_id": 3, "block_id": 3, "deadline": "2026-10-16T13:30:00Z", "progress": 60, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Telegram polling / webhook running", "Basic commands handled"], "description": "Connect telegram bot token and setup message loop.", "verification": None, "blocker": None},
            {"key": "T-5", "title": "Check-in Scheduler & Delivery Loop", "status": "in_progress", "owner_member_id": 3, "block_id": 3, "deadline": "2026-10-16T14:30:00Z", "progress": 40, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Sends check-in messages every cadence", "Handles quiet hours"], "description": "Periodic prompt delivery for member status updates.", "verification": None, "blocker": None},
            {"key": "T-6", "title": "GitHub Commit Poller & Ingestion", "status": "in_progress", "owner_member_id": 4, "block_id": 4, "deadline": "2026-10-16T14:00:00Z", "progress": 50, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Polls repo commits every 45s", "Upserts into commit_log"], "description": "Read commit events and store authored changes.", "verification": None, "blocker": None},
            {"key": "T-7", "title": "Payment & API Integration", "status": "blocked", "owner_member_id": 2, "block_id": 2, "deadline": "2026-10-16T14:30:00Z", "progress": 30, "risk": "at_risk", "is_milestone": False, "acceptance_criteria": ["External API client connected", "Credentials validated"], "description": "Integrate third party API client for downstream processing.", "verification": None, "blocker": {"id": 1, "description": "connected, but waiting for test credentials", "status": "open", "routed_to": None}},
            {"key": "T-8", "title": "Verifier Engine & LLM Diff Inspector", "status": "claimed_done", "owner_member_id": 4, "block_id": 4, "deadline": "2026-10-16T15:00:00Z", "progress": 90, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Inspects git diff against acceptance criteria", "Assigns verdict and confidence"], "description": "LLM verification prompt comparing git commits to criteria.", "verification": {"verdict": "partial", "confidence": 0.60, "reason": "Test suite missing mock responses"}, "blocker": None},
            {"key": "T-9", "title": "Risk Recompute & Slip Detection", "status": "needs_review", "owner_member_id": 2, "block_id": 2, "deadline": "2026-10-16T15:30:00Z", "progress": 85, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Calculates slack and slip", "Emits risk_changed events"], "description": "Ripple effect calculator propagating delay through task DAG.", "verification": {"verdict": "partial", "confidence": 0.50, "reason": "Edge cases with circular slack need review"}, "blocker": None},
            {"key": "T-10", "title": "Contradiction Resolution Logic", "status": "todo", "owner_member_id": 2, "block_id": 2, "deadline": "2026-10-16T16:00:00Z", "progress": 0, "risk": "at_risk", "is_milestone": False, "acceptance_criteria": ["Flags conflicting member claims", "Opens contradiction row"], "description": "Detect opposing status updates across shared dependencies.", "verification": None, "blocker": None},
            {"key": "T-11", "title": "Guide Agent Proactive Digest", "status": "todo", "owner_member_id": 1, "block_id": 1, "deadline": "2026-10-16T16:30:00Z", "progress": 0, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Scans project state every 5 min", "Posts proactive guide notes"], "description": "Autonomous coordinator agent inspecting delays and anomalies.", "verification": None, "blocker": None},
            {"key": "T-12", "title": "Interactive Kanban & DAG Visualization", "status": "todo", "owner_member_id": 3, "block_id": 3, "deadline": "2026-10-16T17:00:00Z", "progress": 0, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Renders tasks and deps", "Updates every 2s via snapshot"], "description": "React board connecting to backend snapshot endpoint.", "verification": None, "blocker": None},
            {"key": "T-13", "title": "Contribution Heatmap & Commit Stats", "status": "todo", "owner_member_id": 4, "block_id": 4, "deadline": "2026-10-16T17:30:00Z", "progress": 0, "risk": "ok", "is_milestone": False, "acceptance_criteria": ["Renders commit timeseries by member", "Shows verified tasks total"], "description": "Contribution visualizer charting commit activity and lines changed.", "verification": None, "blocker": None},
            {"key": "T-14", "title": "Demo & Final Pitch Presentation", "status": "todo", "owner_member_id": 1, "block_id": None, "deadline": "2026-10-16T18:00:00Z", "progress": 0, "risk": "at_risk", "is_milestone": True, "acceptance_criteria": ["Live demo of blocker resolution", "Verification flow displayed"], "description": "Complete working demonstration of Pilot for hackathon judges.", "verification": None, "blocker": None},
        ],
        "deps": [
            {"from": "T-3", "to": "T-1", "kind": "hard"},
            {"from": "T-7", "to": "T-3", "kind": "hard"},
            {"from": "T-10", "to": "T-7", "kind": "hard"},
            {"from": "T-14", "to": "T-10", "kind": "hard"},
        ],
        "events": [],
        "contradictions": [],
        "contributions": {
            "series": {
                "1": [{"ts": "2026-10-16T11:00:00Z", "commits": 2, "lines": 140}],
                "2": [{"ts": "2026-10-16T11:30:00Z", "commits": 1, "lines": 45}],
                "3": [{"ts": "2026-10-16T12:00:00Z", "commits": 3, "lines": 210}],
                "4": [{"ts": "2026-10-16T12:15:00Z", "commits": 1, "lines": 80}],
            },
            "totals": [
                {"member_id": 1, "commits": 2, "lines": 140, "tasks_verified": 1, "last_active": "2026-10-16T11:00:00Z"},
                {"member_id": 2, "commits": 1, "lines": 45, "tasks_verified": 0, "last_active": "2026-10-16T11:30:00Z"},
                {"member_id": 3, "commits": 3, "lines": 210, "tasks_verified": 0, "last_active": "2026-10-16T12:00:00Z"},
                {"member_id": 4, "commits": 1, "lines": 80, "tasks_verified": 0, "last_active": "2026-10-16T12:15:00Z"},
            ],
        },
        "guide_notes": [],
    }


@router.get("/projects/{code}/snapshot")
def get_snapshot(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            if code == "DEMO01":
                return get_mock_snapshot(code)
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        pid = project.id

        # Batch query all entities in parallel / single queries
        members = session.exec(select(Member).where(Member.project_id == pid).order_by(Member.id)).all()
        blocks = session.exec(select(Block).where(Block.project_id == pid).order_by(Block.id)).all()
        tasks = session.exec(select(Task).where(Task.project_id == pid).order_by(Task.key)).all()
        task_ids = {t.id for t in tasks}

        # Task dependencies
        all_deps = session.exec(select(TaskDep)).all()
        task_key_by_id = {t.id: t.key for t in tasks}
        project_deps = [
            d for d in all_deps if d.task_id in task_ids and d.depends_on_task_id in task_key_by_id
        ]

        # Latest verification per task
        all_verifications = session.exec(
            select(Verification).order_by(desc(Verification.created_at))
        ).all()
        latest_verification_by_task: dict[int, Verification] = {}
        for v in all_verifications:
            if v.task_id in task_ids and v.task_id not in latest_verification_by_task:
                latest_verification_by_task[v.task_id] = v

        # Open blocker per task
        all_blockers = session.exec(
            select(Blocker).where(Blocker.status.in_(["open", "routed"])).order_by(desc(Blocker.created_at))
        ).all()
        active_blocker_by_task: dict[int, Blocker] = {}
        for b in all_blockers:
            if b.task_id in task_ids and b.task_id not in active_blocker_by_task:
                active_blocker_by_task[b.task_id] = b

        # Open contradictions
        contradictions = session.exec(
            select(Contradiction).where(Contradiction.project_id == pid, Contradiction.status == "open")
        ).all()

        # Last 100 events
        events = session.exec(
            select(Event).where(Event.project_id == pid).order_by(desc(Event.ts)).limit(100)
        ).all()

        # Guide notes from events
        guide_events = session.exec(
            select(Event).where(Event.project_id == pid, Event.type == "guide_note").order_by(desc(Event.ts)).limit(10)
        ).all()
        guide_notes = [
            {"ts": e.ts.isoformat() if e.ts else "", "note": (e.payload or {}).get("note", "")}
            for e in guide_events
        ]

        # Contributions series & totals
        commit_logs = session.exec(
            select(CommitLog).where(CommitLog.project_id == pid).order_by(CommitLog.committed_at)
        ).all()

        verified_tasks_by_member = defaultdict(int)
        for t in tasks:
            if t.status == "verified_done" and t.owner_member_id:
                verified_tasks_by_member[t.owner_member_id] += 1

        series_by_member: dict[str, list[dict]] = {str(m.id): [] for m in members}
        totals_by_member: dict[int, dict] = {
            m.id: {
                "member_id": m.id,
                "commits": 0,
                "lines": 0,
                "tasks_verified": verified_tasks_by_member[m.id],
                "last_active": None,
            }
            for m in members
        }

        for c in commit_logs:
            if c.member_id and c.member_id in totals_by_member:
                mid = c.member_id
                lines = (c.additions or 0) + (c.deletions or 0)
                totals_by_member[mid]["commits"] += 1
                totals_by_member[mid]["lines"] += lines
                if c.committed_at:
                    c_ts = c.committed_at.isoformat()
                    totals_by_member[mid]["last_active"] = c_ts
                    series_by_member[str(mid)].append({
                        "ts": c_ts,
                        "commits": 1,
                        "lines": lines,
                    })

        # Assemble JSON response exactly matching Section 9.1
        return {
            "project": {
                "code": project.code,
                "name": project.name,
                "status": project.status,
                "repo_url": project.repo_url,
                "starts_at": project.starts_at.isoformat() if project.starts_at else None,
                "ends_at": project.ends_at.isoformat() if project.ends_at else None,
            },
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "role": m.role,
                    "github_login": m.github_login,
                    "invite_status": m.invite_status,
                    "color": PALETTE[(m.id or 0) % len(PALETTE)],
                }
                for m in members
            ],
            "blocks": [
                {
                    "id": b.id,
                    "name": b.name,
                    "owner_member_id": b.owner_member_id,
                    "total_effort": b.total_effort,
                    "oversize_flag": b.oversize_flag,
                }
                for b in blocks
            ],
            "tasks": [
                {
                    "key": t.key,
                    "title": t.title,
                    "status": t.status,
                    "owner_member_id": t.owner_member_id,
                    "block_id": t.block_id,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "progress": t.progress,
                    "risk": t.risk,
                    "is_milestone": t.is_milestone,
                    "acceptance_criteria": t.acceptance_criteria or [],
                    "description": t.description or "",
                    "verification": {
                        "verdict": latest_verification_by_task[t.id].verdict,
                        "confidence": latest_verification_by_task[t.id].confidence,
                        "reason": latest_verification_by_task[t.id].reason or "",
                    }
                    if t.id in latest_verification_by_task
                    else None,
                    "blocker": {
                        "id": active_blocker_by_task[t.id].id,
                        "description": active_blocker_by_task[t.id].description,
                        "status": active_blocker_by_task[t.id].status,
                        "routed_to": active_blocker_by_task[t.id].routed_to_member_id,
                    }
                    if t.id in active_blocker_by_task
                    else None,
                }
                for t in tasks
            ],
            "deps": [
                {
                    "from": task_key_by_id[d.task_id],
                    "to": task_key_by_id[d.depends_on_task_id],
                    "kind": d.kind,
                }
                for d in project_deps
            ],
            "events": [
                {
                    "id": e.id,
                    "project_id": e.project_id,
                    "ts": e.ts.isoformat() if e.ts else "",
                    "actor_member_id": e.actor_member_id,
                    "type": e.type,
                    "task_id": e.task_id,
                    "payload": e.payload or {},
                }
                for e in events
            ],
            "contradictions": [
                {
                    "id": c.id,
                    "project_id": c.project_id,
                    "task_ids": c.task_ids,
                    "member_ids": c.member_ids,
                    "summary": c.summary,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                    "resolution": c.resolution,
                }
                for c in contradictions
            ],
            "contributions": {
                "series": series_by_member,
                "totals": list(totals_by_member.values()),
            },
            "guide_notes": guide_notes,
        }


# ---------------------------------------------------------
# Planning & Scheduling Endpoints
# ---------------------------------------------------------

@router.post("/projects/{code}/plan")
def plan_project(code: str, req: PlanRequest):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        try:
            tasks = generate_plan(
                session=session,
                project_id=project.id,
                idea=req.idea or project.idea,
                team_size=req.team_size,
                skills=req.skills,
                duration_hours=req.duration_hours,
            )
            session.commit()
            return {"task_count": len(tasks), "tasks": [t.key for t in tasks]}
        except PlanGenerationError as e:
            session.rollback()
            raise HTTPException(
                status_code=502,
                detail={"error": f"Failed to generate plan from LLM: {str(e)}", "code": "PLAN_GENERATION_FAILED"},
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500,
                detail={"error": f"Internal planning error: {str(e)}", "code": "PLAN_ERROR"},
            )


@router.post("/projects/{code}/bundle")
def bundle_and_preview_assignment(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        blocks = bundle(session, project.id)
        preview = assign(session, project.id)
        session.commit()
        return preview


@router.post("/projects/{code}/confirm-assignment")
def post_confirm_assignment(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        result = confirm_assignment(session, project.id)
        session.commit()
        return result


@router.post("/projects/{code}/kickoff")
def kickoff_project(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        now = datetime.now(timezone.utc)
        project.status = "running"
        if not project.starts_at:
            project.starts_at = now
        session.add(project)

        add_event(
            session=session,
            project_id=project.id,
            type="status_changed",
            payload={"from_status": "planning", "to_status": "running", "source": "kickoff"},
        )
        session.commit()
        return {"status": "running", "code": project.code}


# ---------------------------------------------------------
# Tasks CRUD
# ---------------------------------------------------------

@router.get("/projects/{code}/tasks")
def list_tasks(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        tasks = session.exec(select(Task).where(Task.project_id == project.id).order_by(Task.key)).all()
        return tasks


@router.post("/projects/{code}/tasks", status_code=status.HTTP_201_CREATED)
def add_task(code: str, req: TaskCreateRequest):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        existing_tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
        next_idx = len(existing_tasks) + 1
        key = f"T-{next_idx}"

        task = Task(
            project_id=project.id,
            key=key,
            title=req.title,
            description=req.description,
            effort=req.effort,
            acceptance_criteria=req.acceptance_criteria,
            status="todo",
            is_milestone=req.is_milestone,
            progress=0,
            risk="ok",
        )
        session.add(task)
        session.flush()

        task_by_key = {t.key: t for t in existing_tasks}
        for dep_key in req.depends_on_keys:
            parent = task_by_key.get(dep_key)
            if parent:
                session.add(TaskDep(task_id=task.id, depends_on_task_id=parent.id, kind="hard"))

        add_event(
            session=session,
            project_id=project.id,
            type="task_created",
            task_id=task.id,
            payload={"key": task.key, "title": task.title},
        )
        session.commit()
        session.refresh(task)
        return task


@router.patch("/projects/{code}/tasks/{key}")
def patch_task(code: str, key: str, req: TaskPatchRequest):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Task '{key}' not found", "code": "TASK_NOT_FOUND"},
            )

        if req.title is not None:
            task.title = req.title
        if req.description is not None:
            task.description = req.description
        if req.effort is not None:
            task.effort = req.effort
        if req.progress is not None:
            task.progress = req.progress
        if req.owner_member_id is not None:
            task.owner_member_id = req.owner_member_id
        if req.acceptance_criteria is not None:
            task.acceptance_criteria = req.acceptance_criteria

        # If status update requested via patch
        if req.status is not None and req.status != task.status:
            try:
                task = transition_task(
                    session=session,
                    task_key=key,
                    project_id=project.id,
                    new_status=req.status,
                    actor_member_id=req.owner_member_id or task.owner_member_id,
                    reason="Manual status patch",
                    source="lead_override" if req.status == "verified_done" else "reply",
                    extra={"progress": req.progress} if req.progress is not None else None,
                )
            except IllegalTransition as e:
                raise HTTPException(
                    status_code=400,
                    detail={"error": str(e), "code": "ILLEGAL_TRANSITION"},
                )

        # Check for cycles if dependencies are updated
        if req.depends_on_keys is not None:
            all_tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
            task_key_to_id = {t.key: t.id for t in all_tasks}

            # Existing graph
            deps = session.exec(select(TaskDep)).all()
            adj = defaultdict(list)
            for d in deps:
                if d.task_id != task.id:
                    adj[d.task_id].append(d.depends_on_task_id)

            # Add prospective new edges
            for parent_key in req.depends_on_keys:
                pid = task_key_to_id.get(parent_key)
                if pid:
                    adj[task.id].append(pid)

            # Cycle detection (DFS)
            visited = set()
            stack = set()

            def dfs(node):
                visited.add(node)
                stack.add(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in stack:
                        return True
                stack.remove(node)
                return False

            has_cycle = any(dfs(t.id) for t in all_tasks if t.id not in visited)
            if has_cycle:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "Dependency update would introduce a cycle", "code": "DEPENDENCY_CYCLE"},
                )

            # Update deps in DB
            session.exec(select(TaskDep).where(TaskDep.task_id == task.id))
            for old_dep in [d for d in deps if d.task_id == task.id]:
                session.delete(old_dep)

            for parent_key in req.depends_on_keys:
                pid = task_key_to_id.get(parent_key)
                if pid:
                    session.add(TaskDep(task_id=task.id, depends_on_task_id=pid, kind="hard"))

        add_event(
            session=session,
            project_id=project.id,
            type="task_updated",
            task_id=task.id,
            payload={"key": task.key, "title": task.title},
        )
        session.commit()
        session.refresh(task)
        return task


@router.delete("/projects/{code}/tasks/{key}")
def delete_task(code: str, key: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Task '{key}' not found", "code": "TASK_NOT_FOUND"},
            )

        task_id = task.id
        # Delete edges
        deps = session.exec(
            select(TaskDep).where(
                (TaskDep.task_id == task_id) | (TaskDep.depends_on_task_id == task_id)
            )
        ).all()
        for d in deps:
            session.delete(d)

        session.delete(task)
        add_event(
            session=session,
            project_id=project.id,
            type="task_updated",
            payload={"action": "deleted", "key": key},
        )
        session.commit()
        return {"status": "deleted", "key": key}


@router.post("/projects/{code}/tasks/{key}/override-verify")
def override_verify_task(code: str, key: str):
    """
    Lead manually forces verified_done on a task.
    """
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Task '{key}' not found", "code": "TASK_NOT_FOUND"},
            )

        # Ensure task is eligible for override
        if task.status not in {"claimed_done", "needs_review"}:
            # Move to claimed_done first or transition directly if from needs_review
            pass

        try:
            task = transition_task(
                session=session,
                task_key=key,
                project_id=project.id,
                new_status="verified_done",
                actor_member_id=project.lead_member_id,
                reason="Lead manual override verification",
                source="lead_override",
            )
            session.commit()
            session.refresh(task)
            return {"status": "verified_done", "key": task.key}
        except IllegalTransition as e:
            raise HTTPException(
                status_code=400,
                detail={"error": str(e), "code": "ILLEGAL_TRANSITION"},
            )


# ---------------------------------------------------------
# Members, Blockers, Contradictions, Events
# ---------------------------------------------------------

@router.get("/projects/{code}/members")
def get_members(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )
        return session.exec(select(Member).where(Member.project_id == project.id)).all()


@router.get("/projects/{code}/blockers")
def get_blockers(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )
        tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
        t_ids = {t.id for t in tasks}
        blockers = session.exec(select(Blocker).where(Blocker.task_id.in_(t_ids))).all()
        return blockers


@router.get("/projects/{code}/contradictions")
def get_contradictions(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )
        return session.exec(select(Contradiction).where(Contradiction.project_id == project.id)).all()


@router.get("/projects/{code}/events")
def get_events(
    code: str,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        events = session.exec(
            select(Event)
            .where(Event.project_id == project.id)
            .order_by(desc(Event.ts))
            .offset(offset)
            .limit(limit)
        ).all()
        return events


@router.post("/projects/{code}/ask")
def ask_guide(code: str, req: AskRequest):
    from backend.guide import run_guide_query

    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        result = run_guide_query(session, project.id, req.question)
        return result


@router.post("/projects/{code}/report")
def get_project_report(code: str):
    from backend.guide import generate_report

    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Project '{code}' not found", "code": "PROJECT_NOT_FOUND"},
            )

        report = generate_report(session, project.id)
        return report

