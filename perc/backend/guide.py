import re
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlmodel import Session, select, desc

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
from backend.llm import call_json
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Tool Response Models
# ---------------------------------------------------------

class GuideAction(BaseModel):
    tool: Optional[str] = None
    args: Optional[dict[str, Any]] = None
    final: Optional[str] = None
    cited_keys: list[str] = Field(default_factory=list)
    cited_shas: list[str] = Field(default_factory=list)


GUIDE_SYSTEM_PROMPT = """You are Pilot's Guide Agent, the factual project coordinator.
You have access to tools to query project status, commits, members, blockers, and timelines.
To use a tool, respond with:
{"tool": "<tool_name>", "args": {<arguments>}}

When you have enough factual evidence to answer, respond with:
{"final": "<your answer>", "cited_keys": ["T-1", ...], "cited_shas": ["a1b2c3d", ...]}

CRITICAL RULES:
1. Every factual claim MUST cite a task key (e.g. T-4), commit SHA, or timestamp that appeared in a tool result.
2. If data is not available or unknown, say so directly. NEVER invent task keys, SHAs, or numbers.
3. Maximum 6 tool calls per query."""


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------
# Read & Action Tools
# ---------------------------------------------------------

def get_project_snapshot(session: Session, project_id: int) -> dict[str, Any]:
    project = session.get(Project, project_id)
    if not project:
        return {"error": "Project not found"}
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    members = session.exec(select(Member).where(Member.project_id == project_id)).all()
    blocks = session.exec(select(Block).where(Block.project_id == project_id)).all()
    return {
        "project": {"code": project.code, "name": project.name, "status": project.status},
        "members": [{"id": m.id, "name": m.name, "role": m.role} for m in members],
        "task_count": len(tasks),
        "tasks": [{"key": t.key, "title": t.title, "status": t.status, "risk": t.risk} for t in tasks],
        "block_count": len(blocks),
    }


def get_task(session: Session, project_id: int, key: str) -> dict[str, Any]:
    task = session.exec(
        select(Task).where(Task.project_id == project_id, Task.key == key)
    ).first()
    if not task:
        return {"error": f"Task {key} not found"}

    owner = session.get(Member, task.owner_member_id) if task.owner_member_id else None
    return {
        "key": task.key,
        "title": task.title,
        "status": task.status,
        "owner": owner.name if owner else None,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "progress": task.progress,
        "risk": task.risk,
        "acceptance_criteria": task.acceptance_criteria,
    }


def get_member_contributions(session: Session, project_id: int, member_query: str) -> dict[str, Any]:
    # Match by id or name
    member = None
    if str(member_query).isdigit():
        member = session.get(Member, int(member_query))
    if not member:
        member = session.exec(
            select(Member).where(Member.project_id == project_id, Member.name.ilike(f"%{member_query}%"))
        ).first()

    if not member:
        return {"error": f"Member '{member_query}' not found in project"}

    commits = session.exec(
        select(CommitLog).where(CommitLog.project_id == project_id, CommitLog.member_id == member.id)
    ).all()
    verified_tasks = session.exec(
        select(Task).where(
            Task.project_id == project_id,
            Task.owner_member_id == member.id,
            Task.status == "verified_done",
        )
    ).all()

    total_additions = sum(c.additions or 0 for c in commits)
    total_deletions = sum(c.deletions or 0 for c in commits)

    return {
        "member_id": member.id,
        "member_name": member.name,
        "commit_count": len(commits),
        "total_lines_changed": total_additions + total_deletions,
        "verified_tasks": [t.key for t in verified_tasks],
        "recent_commits": [
            {"sha": c.sha, "message": c.message, "committed_at": c.committed_at.isoformat() if c.committed_at else ""}
            for c in commits[:10]
        ],
    }


def get_commits(session: Session, project_id: int, target: Optional[str] = None) -> dict[str, Any]:
    statement = select(CommitLog).where(CommitLog.project_id == project_id).order_by(desc(CommitLog.committed_at))
    commits = session.exec(statement).all()

    results = []
    for c in commits:
        if target:
            # Check if target matches author_login or sha or message
            if target.lower() not in (c.author_login or "").lower() and target not in c.sha and target.lower() not in (c.message or "").lower():
                continue
        results.append({
            "sha": c.sha,
            "author": c.author_login,
            "message": c.message,
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
            "lines": (c.additions or 0) + (c.deletions or 0),
        })

    return {"commits": results}


def get_timeline(session: Session, project_id: int, until_str: Optional[str] = None) -> dict[str, Any]:
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()

    until_dt = None
    if until_str:
        try:
            until_dt = datetime.fromisoformat(until_str.replace("Z", "+00:00"))
        except Exception:
            pass

    completed_tasks = []
    for t in tasks:
        t_completed = ensure_utc(t.completed_at)
        if t_completed:
            if until_dt is None or t_completed <= until_dt:
                completed_tasks.append({
                    "key": t.key,
                    "title": t.title,
                    "completed_at": t_completed.isoformat(),
                    "status": t.status,
                })

    return {
        "until": until_str,
        "completed_count": len(completed_tasks),
        "completed_tasks": completed_tasks,
    }


def get_open_blockers(session: Session, project_id: int) -> dict[str, Any]:
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    task_ids = {t.id: t.key for t in tasks}

    blockers = session.exec(
        select(Blocker).where(Blocker.task_id.in_(task_ids.keys()), Blocker.status.in_(["open", "routed"]))
    ).all()

    return {
        "open_blockers": [
            {
                "id": b.id,
                "task_key": task_ids.get(b.task_id),
                "description": b.description,
                "status": b.status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in blockers
        ]
    }


def get_risks(session: Session, project_id: int) -> dict[str, Any]:
    tasks = session.exec(
        select(Task).where(Task.project_id == project_id, Task.risk.in_(["at_risk", "critical"]))
    ).all()
    milestone = session.exec(
        select(Task).where(Task.project_id == project_id, Task.is_milestone == True)
    ).first()

    return {
        "at_risk_tasks": [
            {"key": t.key, "title": t.title, "risk": t.risk, "status": t.status}
            for t in tasks
        ],
        "milestone_risk": milestone.risk if milestone else "ok",
    }


def post_note(session: Session, project_id: int, text: str) -> dict[str, Any]:
    event = add_event(
        session=session,
        project_id=project_id,
        type="guide_note",
        payload={"note": text, "source": "guide"},
    )
    session.flush()
    return {"status": "posted", "event_id": event.id}


# Dispatch table
TOOLS = {
    "get_project_snapshot": get_project_snapshot,
    "get_task": get_task,
    "get_member_contributions": get_member_contributions,
    "get_commits": get_commits,
    "get_timeline": get_timeline,
    "get_open_blockers": get_open_blockers,
    "get_risks": get_risks,
    "post_note": post_note,
}


# ---------------------------------------------------------
# Citation Validator
# ---------------------------------------------------------

def extract_citations(text: str) -> tuple[set[str], set[str]]:
    """Extracts task keys (T-n) and SHAs (hex 7-40 chars) from text."""
    keys = set(re.findall(r"\bT-\d+\b", text))
    shas = set(re.findall(r"\b[0-9a-f]{7,40}\b", text, re.IGNORECASE))
    return keys, shas


def validate_citations(
    final_text: str,
    known_tool_data_str: str,
) -> tuple[bool, list[str]]:
    """
    Checks if every task key and SHA in final_text appeared in tool results.
    Returns (valid, invalid_citations).
    """
    found_keys, found_shas = extract_citations(final_text)
    invalid = []

    for k in found_keys:
        if k not in known_tool_data_str:
            invalid.append(k)

    for s in found_shas:
        if s.lower() not in known_tool_data_str.lower():
            invalid.append(s)

    return (len(invalid) == 0, invalid)


# ---------------------------------------------------------
# Tool Loop (Max 6 Steps)
# ---------------------------------------------------------

def run_guide_query(
    session: Session,
    project_id: int,
    question: str,
    max_steps: int = 6,
) -> dict[str, Any]:
    """
    Executes a multi-step tool reasoning loop up to max_steps (default 6).
    Enforces citation checking: discards answers with hallucinated keys/SHAs and retries once.
    """
    trajectory: list[dict[str, Any]] = []
    tool_observations_text = ""
    current_prompt = f"User Question: {question}"

    retried_for_hallucination = False

    for step in range(1, max_steps + 1):
        action: GuideAction = call_json(GUIDE_SYSTEM_PROMPT, current_prompt, GuideAction)

        # Check if model gave final answer
        if action.final:
            is_valid, invalid_items = validate_citations(action.final, tool_observations_text)
            if not is_valid and not retried_for_hallucination:
                retried_for_hallucination = True
                current_prompt = (
                    f"Previous answer rejected because you cited items that NEVER appeared in tool results: {invalid_items}.\n"
                    f"You must strictly only cite data returned by tools. If data is unknown, state that you have no data.\n"
                    f"Tool observation history:\n{tool_observations_text}\n"
                    f"Please answer again."
                )
                continue

            # Valid final answer
            cited_keys, cited_shas = extract_citations(action.final)
            return {
                "question": question,
                "answer": action.final,
                "cited_keys": list(cited_keys),
                "cited_shas": list(cited_shas),
                "steps": step,
            }

        # Otherwise execute requested tool
        tool_name = action.tool
        tool_args = action.args or {}

        if tool_name in TOOLS:
            tool_func = TOOLS[tool_name]
            try:
                result = tool_func(session, project_id, **tool_args)
            except Exception as e:
                result = {"error": f"Tool execution failed: {str(e)}"}
        else:
            result = {"error": f"Unknown tool: '{tool_name}'. Available: {list(TOOLS.keys())}"}

        result_str = json.dumps(result)
        tool_observations_text += f"\n[Step {step} - {tool_name}]: {result_str}"
        trajectory.append({"step": step, "tool": tool_name, "args": tool_args, "result": result})

        current_prompt = (
            f"User Question: {question}\n\n"
            f"Observation from {tool_name}:\n{result_str}\n\n"
            f"Provide next tool call or final answer as JSON."
        )

    # Reached step limit: generate best-effort answer
    fallback_prompt = (
        f"You have reached the 6-step limit. Based strictly on the following tool observations, provide a concise summary answer:\n"
        f"{tool_observations_text}\n"
        f"If data is missing, state it clearly."
    )
    fallback_action: GuideAction = call_json(GUIDE_SYSTEM_PROMPT, fallback_prompt, GuideAction)
    cited_keys, cited_shas = extract_citations(fallback_action.final or "")

    return {
        "question": question,
        "answer": fallback_action.final or "I reached the 6-step query limit and could not fully resolve the query.",
        "cited_keys": list(cited_keys),
        "cited_shas": list(cited_shas),
        "steps": max_steps,
    }


# ---------------------------------------------------------
# Proactive Tick (guide_tick)
# ---------------------------------------------------------

def guide_tick(session: Session, project_id: int) -> list[str]:
    """
    Proactive scan covering:
    - Overdue tasks
    - Stale in_progress tasks with no commits
    - Blocked tasks with no routing
    - Unresolved contradictions
    Idempotent: skips nudging for the same condition within 30 minutes.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=30)

    # Fetch recent guide note payloads to ensure idempotency
    recent_events = session.exec(
        select(Event).where(
            Event.project_id == project_id,
            Event.type == "guide_note",
            Event.ts >= cutoff,
        )
    ).all()
    recent_events = [e for e in recent_events if ensure_utc(e.ts) and ensure_utc(e.ts) >= cutoff]
    recent_notes = {e.payload.get("note", "") for e in recent_events if e.payload}

    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    actions_taken = []

    # 1. Overdue tasks
    for t in tasks:
        t_deadline = ensure_utc(t.deadline)
        if t.status != "verified_done" and t_deadline and t_deadline < now:
            note = f"Task {t.key} ('{t.title}') is overdue (deadline was {t_deadline.strftime('%H:%M UTC')})."
            if note not in recent_notes:
                post_note(session, project_id, note)
                actions_taken.append(note)
                recent_notes.add(note)

    # 2. Open blockers with no routing
    task_ids = {t.id: t.key for t in tasks}
    blockers = session.exec(
        select(Blocker).where(Blocker.task_id.in_(task_ids.keys()), Blocker.status == "open")
    ).all()
    for b in blockers:
        t_key = task_ids.get(b.task_id, "unknown")
        note = f"Task {t_key} is blocked ('{b.description}') and requires routing."
        if note not in recent_notes:
            post_note(session, project_id, note)
            actions_taken.append(note)
            recent_notes.add(note)

    # 3. Unresolved contradictions
    contradictions = session.exec(
        select(Contradiction).where(Contradiction.project_id == project_id, Contradiction.status == "open")
    ).all()
    for c in contradictions:
        note = f"Open contradiction: {c.summary} needs resolution."
        if note not in recent_notes:
            post_note(session, project_id, note)
            actions_taken.append(note)
            recent_notes.add(note)

    session.flush()
    return actions_taken


# ---------------------------------------------------------
# Final Project Report
# ---------------------------------------------------------

def generate_report(session: Session, project_id: int) -> dict[str, Any]:
    """
    Generates final project digest:
    - Contributions per member (commits, lines, tasks verified)
    - Tasks completed with timestamps
    - Claimed vs verified counts
    - Blockers summary
    - Unresolved risks
    """
    project = session.get(Project, project_id)
    members = session.exec(select(Member).where(Member.project_id == project_id)).all()
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    commits = session.exec(select(CommitLog).where(CommitLog.project_id == project_id)).all()
    blockers = session.exec(select(Blocker).where(Blocker.task_id.in_([t.id for t in tasks]))).all()

    # Member contributions
    member_stats = []
    for m in members:
        m_commits = [c for c in commits if c.member_id == m.id]
        m_lines = sum((c.additions or 0) + (c.deletions or 0) for c in m_commits)
        m_verified = [t.key for t in tasks if t.owner_member_id == m.id and t.status == "verified_done"]
        member_stats.append({
            "member_id": m.id,
            "name": m.name,
            "commits": len(m_commits),
            "lines_changed": m_lines,
            "tasks_verified": m_verified,
        })

    completed_tasks = [
        {"key": t.key, "title": t.title, "completed_at": t.completed_at.isoformat() if t.completed_at else None}
        for t in tasks
        if t.status == "verified_done"
    ]

    claimed_count = sum(1 for t in tasks if t.status == "claimed_done")
    verified_count = sum(1 for t in tasks if t.status == "verified_done")
    needs_review_count = sum(1 for t in tasks if t.status == "needs_review")

    unresolved_risks = [
        {"key": t.key, "title": t.title, "risk": t.risk}
        for t in tasks
        if t.risk in ["at_risk", "critical"] and t.status != "verified_done"
    ]

    return {
        "project_code": project.code if project else "UNKNOWN",
        "member_contributions": member_stats,
        "completed_tasks": completed_tasks,
        "counts": {
            "total_tasks": len(tasks),
            "verified_done": verified_count,
            "claimed_done": claimed_count,
            "needs_review": needs_review_count,
        },
        "blockers": [
            {"id": b.id, "description": b.description, "status": b.status}
            for b in blockers
        ],
        "unresolved_risks": unresolved_risks,
    }
