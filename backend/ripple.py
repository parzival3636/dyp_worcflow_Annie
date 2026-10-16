from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from collections import defaultdict, deque
from sqlmodel import Session, select

try:
    from models import Project, Member, Task, TaskDep, Blocker, Event
    from events import add_event
except ImportError:
    from backend.models import Project, Member, Task, TaskDep, Blocker, Event
    from backend.events import add_event


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_effort_hours(task: Task, total_effort: int, window_hours: float) -> float:
    effort = task.effort or 1
    if total_effort <= 0:
        return 1.0
    return (effort / total_effort) * window_hours


def get_task_base_slip(task: Task, now: datetime, latest_blocker: Optional[Blocker] = None) -> float:
    if task.status == "verified_done":
        return 0.0

    deadline = ensure_utc(task.deadline)
    late_hours = 0.0
    if deadline and now > deadline:
        late_hours = (now - deadline).total_seconds() / 3600.0

    blocked_hours = 0.0
    if task.status == "blocked":
        blocked_since = ensure_utc(latest_blocker.created_at) if latest_blocker else None
        if blocked_since and now > blocked_since:
            blocked_hours = (now - blocked_since).total_seconds() / 3600.0
        else:
            blocked_hours = 1.0

    return max(0.0, late_hours, blocked_hours)


def compute_slack(u: Task, v: Task, effort_hours_v: float) -> float:
    d_u = ensure_utc(u.deadline)
    d_v = ensure_utc(v.deadline)
    if not d_u or not d_v:
        return 0.0
    diff_hours = (d_v - d_u).total_seconds() / 3600.0
    return max(0.0, diff_hours - effort_hours_v)


def risk_recompute(session: Session, project_id: int) -> dict[str, Any]:
    project = session.get(Project, project_id)
    if not project:
        return {"error": "Project not found"}

    now = datetime.now(timezone.utc)
    starts_at = ensure_utc(project.starts_at) or now
    ends_at = ensure_utc(project.ends_at) or (starts_at + timedelta(hours=20))
    window_hours = max(0.5, (ends_at - starts_at).total_seconds() / 3600.0)

    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    if not tasks:
        return {"status": "ok", "changes": 0}

    task_map = {t.id: t for t in tasks}
    total_effort = sum(t.effort or 1 for t in tasks)

    blockers = session.exec(
        select(Blocker).where(Blocker.status.in_(["open", "routed"]))
    ).all()
    latest_blocker_by_task = {}
    for b in blockers:
        if b.task_id in task_map:
            latest_blocker_by_task[b.task_id] = b

    deps = session.exec(select(TaskDep)).all()
    project_deps = [d for d in deps if d.task_id in task_map and d.depends_on_task_id in task_map]

    adj = defaultdict(list)
    in_degree = {t.id: 0 for t in tasks}
    predecessors = defaultdict(list)

    for d in project_deps:
        u_id = d.depends_on_task_id
        v_id = d.task_id
        adj[u_id].append(v_id)
        in_degree[v_id] += 1
        predecessors[v_id].append(u_id)

    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    topo_order: list[int] = []
    while queue:
        curr = queue.popleft()
        topo_order.append(curr)
        for nxt in adj[curr]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    for t in tasks:
        if t.id not in topo_order:
            topo_order.append(t.id)

    slip: dict[int, float] = {}
    cause_key: dict[int, Optional[str]] = {}

    for tid in topo_order:
        t = task_map[tid]
        base_slip = get_task_base_slip(t, now, latest_blocker_by_task.get(tid))
        slip[tid] = base_slip
        cause_key[tid] = t.key if base_slip > 0 else None

    for u_id in topo_order:
        u_task = task_map[u_id]
        u_slip = slip[u_id]

        for v_id in adj[u_id]:
            v_task = task_map[v_id]
            eff_v = compute_effort_hours(v_task, total_effort, window_hours)
            slack_uv = compute_slack(u_task, v_task, eff_v)

            propagated_slip = max(0.0, u_slip - slack_uv)
            if propagated_slip > slip[v_id]:
                slip[v_id] = propagated_slip
                cause_key[v_id] = cause_key[u_id]

    changes = 0
    milestone_tasks = [t for t in tasks if t.is_milestone]

    for tid in topo_order:
        t = task_map[tid]
        old_risk = t.risk or "ok"

        if t.status == "verified_done":
            new_risk = "ok"
        elif t.is_milestone:
            preds = predecessors.get(tid, [])
            if preds:
                pred_risks = [task_map[p].risk for p in preds]
                if "critical" in pred_risks:
                    new_risk = "critical"
                elif "at_risk" in pred_risks:
                    new_risk = "at_risk"
                else:
                    new_risk = "ok"
            else:
                new_risk = "ok"
        else:
            task_slip = slip[tid]
            deadline = ensure_utc(t.deadline)
            hours_left = (deadline - now).total_seconds() / 3600.0 if deadline else 24.0

            out_slacks = [
                compute_slack(t, task_map[nxt], compute_effort_hours(task_map[nxt], total_effort, window_hours))
                for nxt in adj[tid]
            ]
            effective_slack = min(out_slacks) if out_slacks else 2.0

            if task_slip > effective_slack and (hours_left <= 12.0 or (deadline and now > deadline)):
                new_risk = "critical"
            elif task_slip > 0.5 * effective_slack:
                new_risk = "at_risk"
            else:
                new_risk = "ok"

        if new_risk != old_risk:
            t.risk = new_risk
            session.add(t)
            changes += 1

            add_event(
                session=session,
                project_id=project_id,
                type="risk_changed",
                task_id=t.id,
                payload={
                    "old_risk": old_risk,
                    "new_risk": new_risk,
                    "cause_task_key": cause_key.get(tid),
                    "slip_hours": round(slip[tid], 2),
                },
            )

    for m in milestone_tasks:
        old_m_risk = m.risk
        preds = predecessors.get(m.id, [])
        pred_risks = [task_map[p].risk for p in preds] if preds else []
        if "critical" in pred_risks:
            new_m_risk = "critical"
        elif "at_risk" in pred_risks:
            new_m_risk = "at_risk"
        else:
            new_m_risk = "ok"

        if new_m_risk != old_m_risk:
            m.risk = new_m_risk
            session.add(m)
            changes += 1
            add_event(
                session=session,
                project_id=project_id,
                type="risk_changed",
                task_id=m.id,
                payload={
                    "old_risk": old_m_risk,
                    "new_risk": new_m_risk,
                    "cause_task_key": cause_key.get(m.id),
                },
            )

    session.flush()
    return {"status": "ok", "changes": changes}


def ripple_caption(session: Session, project_id: int) -> str:
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    blocked_tasks = [t for t in tasks if t.status == "blocked"]
    milestone = next((t for t in tasks if t.is_milestone), None)

    if not blocked_tasks:
        at_risk_tasks = [t for t in tasks if t.risk in ["at_risk", "critical"]]
        if not at_risk_tasks:
            return "All tasks are on track and progressing normally."
        first_risk = at_risk_tasks[0]
        return f"Task {first_risk.key} ('{first_risk.title}') is {first_risk.risk}."

    first_blocked = blocked_tasks[0]
    owner = session.get(Member, first_blocked.owner_member_id) if first_blocked.owner_member_id else None
    owner_name = owner.name if owner else "A member"

    if milestone and milestone.risk in ["at_risk", "critical"]:
        return f"{owner_name} is blocked on {first_blocked.key}, so the {milestone.title} is {milestone.risk}."

    return f"{owner_name} is blocked on {first_blocked.key} ({first_blocked.title})."
