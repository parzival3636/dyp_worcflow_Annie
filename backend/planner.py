import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from collections import defaultdict, deque

from sqlmodel import Session, select

try:
    from config import settings
    from models import Project, Member, Block, Task, TaskDep
    from events import add_event
    from llm import call_json, P2Plan, P2Task, PlanGenerationError
    from prompts import P2_PLAN_PROMPT
except ImportError:
    from backend.config import settings
    from backend.models import Project, Member, Block, Task, TaskDep
    from backend.events import add_event
    from backend.llm import call_json, P2Plan, P2Task, PlanGenerationError
    from backend.prompts import P2_PLAN_PROMPT


def sanitize_task_titles(tasks: list[P2Task]) -> list[P2Task]:
    seen: dict[str, int] = {}
    title_map: dict[str, str] = {}
    renamed_tasks: list[P2Task] = []

    for task in tasks:
        original_title = task.title.strip()
        count = seen.get(original_title, 0) + 1
        seen[original_title] = count

        if count == 1:
            new_title = original_title
        else:
            new_title = f"{original_title} ({count})"

        title_map[original_title] = new_title
        renamed_tasks.append(
            P2Task(
                title=new_title,
                description=task.description,
                acceptance_criteria=task.acceptance_criteria,
                effort=task.effort,
                depends_on=list(task.depends_on),
                is_milestone=task.is_milestone,
            )
        )

    for t in renamed_tasks:
        updated_deps = [title_map.get(dep, dep) for dep in t.depends_on if dep != t.title]
        t.depends_on = updated_deps

    return renamed_tasks


def prune_unknown_deps(tasks: list[P2Task]) -> list[P2Task]:
    all_titles = {t.title for t in tasks}
    for t in tasks:
        t.depends_on = [dep for dep in t.depends_on if dep in all_titles and dep != t.title]
    return tasks


def remove_dependency_cycles(tasks: list[P2Task]) -> list[P2Task]:
    task_by_title = {t.title: t for t in tasks}
    state: dict[str, int] = {t.title: 0 for t in tasks}

    def dfs(title: str):
        state[title] = 1
        t = task_by_title.get(title)
        if not t:
            state[title] = 2
            return

        surviving_deps = []
        for dep in t.depends_on:
            dep_state = state.get(dep, 0)
            if dep_state == 1:
                continue
            elif dep_state == 0:
                dfs(dep)
            surviving_deps.append(dep)

        t.depends_on = surviving_deps
        state[title] = 2

    for t in tasks:
        if state[t.title] == 0:
            dfs(t.title)

    return tasks


def ensure_milestone(tasks: list[P2Task]) -> list[P2Task]:
    if not tasks:
        return tasks

    if not any(t.is_milestone for t in tasks):
        last_task = tasks[-1]
        last_task.is_milestone = True
        if "demo" not in last_task.title.lower():
            last_task.title = f"{last_task.title} (Demo)"
    return tasks


def validate_and_sanitize_tasks(raw_tasks: list[P2Task]) -> list[P2Task]:
    tasks = sanitize_task_titles(raw_tasks)
    tasks = prune_unknown_deps(tasks)
    tasks = remove_dependency_cycles(tasks)
    tasks = ensure_milestone(tasks)
    return tasks


def generate_plan(
    session: Session,
    project_id: int,
    idea: Optional[str] = None,
    team_size: int = 4,
    skills: Optional[list[str]] = None,
    duration_hours: int = 20,
) -> list[Task]:
    project = session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    prompt_idea = idea or project.idea or project.description or project.name
    skills_str = ", ".join(skills) if skills else "General Full-stack"
    fr_str = f"\nFunctional Requirements:\n{project.functional_requirements}" if project.functional_requirements else ""
    nfr_str = f"\nNon-Functional Reqs & Constraints:\n{project.non_functional_requirements}" if project.non_functional_requirements else ""

    user_prompt = (
        f"Project Name: {project.name}\n"
        f"Project Idea: {prompt_idea}{fr_str}{nfr_str}\n"
        f"Team Size: {team_size}\n"
        f"Skills Available: {skills_str}\n"
        f"Duration Window: {duration_hours} hours\n"
        f"Generate 12 to 20 engineering tasks forming an acyclic dependency graph."
    )

    plan_response: P2Plan = call_json(P2_PLAN_PROMPT, user_prompt, P2Plan)
    validated_tasks = validate_and_sanitize_tasks(plan_response.tasks)

    # Protect started tasks on re-generation
    existing_tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    has_active_work = any(t.status not in ("todo", "backlog") for t in existing_tasks)
    if not has_active_work:
        for et in existing_tasks:
            session.delete(et)
        session.flush()

    project.plan_status = "generated"
    session.add(project)

    inserted_tasks: list[Task] = []
    title_to_task: dict[str, Task] = {}

    for idx, p2_task in enumerate(validated_tasks, start=1):
        task_key = f"T-{idx}"
        task = Task(
            project_id=project_id,
            key=task_key,
            title=p2_task.title,
            description=p2_task.description,
            acceptance_criteria=p2_task.acceptance_criteria,
            effort=p2_task.effort,
            status="todo",
            is_milestone=p2_task.is_milestone,
            progress=0,
            risk="ok",
        )
        session.add(task)
        inserted_tasks.append(task)
        title_to_task[p2_task.title] = task

    session.flush()

    for p2_task in validated_tasks:
        dependent_task = title_to_task[p2_task.title]
        for dep_title in p2_task.depends_on:
            prerequisite_task = title_to_task.get(dep_title)
            if prerequisite_task and prerequisite_task.id != dependent_task.id:
                dep_row = TaskDep(
                    task_id=dependent_task.id,
                    depends_on_task_id=prerequisite_task.id,
                    kind="hard",
                )
                session.add(dep_row)

    for task in inserted_tasks:
        add_event(
            session=session,
            project_id=project_id,
            type="task_created",
            task_id=task.id,
            payload={"key": task.key, "title": task.title, "effort": task.effort},
        )

    session.flush()

    # Automatically bundle and assign to available project members
    try:
        bundle(session, project_id)
        assign(session, project_id)
    except Exception:
        pass

    return inserted_tasks


class UnionFind:
    def __init__(self, elements):
        self.parent = {x: x for x in elements}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_y] = root_x


def bundle(session: Session, project_id: int) -> list[Block]:
    tasks = session.exec(
        select(Task).where(Task.project_id == project_id)
    ).all()
    if not tasks:
        return []

    non_milestones = [t for t in tasks if not t.is_milestone]
    milestones = [t for t in tasks if t.is_milestone]

    for m in milestones:
        m.block_id = None
        session.add(m)

    if not non_milestones:
        session.flush()
        return []

    task_ids = {t.id for t in non_milestones}
    uf = UnionFind(task_ids)

    deps = session.exec(
        select(TaskDep).where(TaskDep.kind == "hard")
    ).all()

    for dep in deps:
        if dep.task_id in task_ids and dep.depends_on_task_id in task_ids:
            uf.union(dep.task_id, dep.depends_on_task_id)

    components: dict[int, list[Task]] = defaultdict(list)
    task_map = {t.id: t for t in non_milestones}
    for tid in task_ids:
        root = uf.find(tid)
        components[root].append(task_map[tid])

    existing_blocks = session.exec(
        select(Block).where(Block.project_id == project_id)
    ).all()
    for eb in existing_blocks:
        session.delete(eb)
    session.flush()

    new_blocks: list[Block] = []
    sorted_roots = sorted(components.keys(), key=lambda r: min(t.id for t in components[r]))

    for root in sorted_roots:
        block_tasks = components[root]
        total_effort = sum(t.effort or 1 for t in block_tasks)
        heaviest_task = max(block_tasks, key=lambda t: (t.effort or 1, -(t.id or 0)))
        block_name = heaviest_task.title or f"Block {len(new_blocks) + 1}"

        block = Block(
            project_id=project_id,
            name=block_name,
            total_effort=total_effort,
            oversize_flag=False,
        )
        session.add(block)
        session.flush()

        for t in block_tasks:
            t.block_id = block.id
            session.add(t)

        new_blocks.append(block)

    session.flush()
    return new_blocks


def topological_sort(tasks: list[Task], deps: list[TaskDep]) -> list[Task]:
    task_map = {t.id: t for t in tasks}
    in_degree = {t.id: 0 for t in tasks}
    graph = defaultdict(list)

    for d in deps:
        if d.task_id in in_degree and d.depends_on_task_id in in_degree:
            graph[d.depends_on_task_id].append(d.task_id)
            in_degree[d.task_id] += 1

    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    ordered: list[Task] = []

    while queue:
        curr_id = queue.popleft()
        ordered.append(task_map[curr_id])
        for nxt in graph[curr_id]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    if len(ordered) < len(tasks):
        remaining = [t for t in tasks if t not in ordered]
        ordered.extend(remaining)

    return ordered


def propose_split(session: Session, block_id: int) -> dict[str, Any]:
    block = session.get(Block, block_id)
    if not block:
        raise ValueError(f"Block {block_id} not found")

    tasks = session.exec(select(Task).where(Task.block_id == block_id)).all()
    if len(tasks) < 2:
        return {"error": "Block must contain at least 2 tasks to split"}

    task_ids = {t.id for t in tasks}
    deps = session.exec(
        select(TaskDep).where(TaskDep.kind == "hard")
    ).all()
    block_deps = [d for d in deps if d.task_id in task_ids and d.depends_on_task_id in task_ids]

    ordered_tasks = topological_sort(tasks, block_deps)

    best_split_idx = 1
    min_diff = float("inf")
    total_effort = sum(t.effort or 1 for t in ordered_tasks)

    curr_left_sum = 0
    for i in range(1, len(ordered_tasks)):
        curr_left_sum += ordered_tasks[i - 1].effort or 1
        right_sum = total_effort - curr_left_sum
        diff = abs(curr_left_sum - right_sum)
        if diff < min_diff:
            min_diff = diff
            best_split_idx = i

    left_tasks = ordered_tasks[:best_split_idx]
    right_tasks = ordered_tasks[best_split_idx:]
    left_ids = {t.id for t in left_tasks}
    right_ids = {t.id for t in right_tasks}

    cut_edges = []
    for d in block_deps:
        if (d.task_id in right_ids and d.depends_on_task_id in left_ids) or \
           (d.task_id in left_ids and d.depends_on_task_id in right_ids):
            cut_edges.append({"task_id": d.task_id, "depends_on_task_id": d.depends_on_task_id})

    return {
        "block_id": block_id,
        "left_tasks": [t.key for t in left_tasks],
        "right_tasks": [t.key for t in right_tasks],
        "left_effort": sum(t.effort or 1 for t in left_tasks),
        "right_effort": sum(t.effort or 1 for t in right_tasks),
        "imbalance": min_diff,
        "cut_edges": cut_edges,
    }


def token_overlap(text1: str, text2: str) -> int:
    words1 = set(re.findall(r"\w+", (text1 or "").lower()))
    words2 = set(re.findall(r"\w+", (text2 or "").lower()))
    return len(words1.intersection(words2))


def assign(session: Session, project_id: int) -> dict[str, Any]:
    project = session.get(Project, project_id)
    blocks = session.exec(
        select(Block).where(Block.project_id == project_id)
    ).all()
    members = session.exec(
        select(Member).where(Member.project_id == project_id).order_by(Member.id)
    ).all()

    if not blocks or not members:
        return {"blocks": [], "loads": {}, "oversize_warnings": []}

    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    n_members = len(members)

    # If there are more members than blocks, auto-split oversize/splittable blocks
    # so every teammate gets independent modules and fair work share.
    if n_members > len(blocks) and len(blocks) > 0:
        max_splits = n_members - len(blocks)
        for _ in range(max_splits):
            current_blocks = session.exec(select(Block).where(Block.project_id == project_id)).all()
            splittable = []
            for b in current_blocks:
                b_tasks = [t for t in tasks if t.block_id == b.id]
                if len(b_tasks) >= 2:
                    splittable.append((b, sum(t.effort or 1 for t in b_tasks)))
            if not splittable:
                break
            largest_b, _ = max(splittable, key=lambda x: x[1])
            proposal = propose_split(session, largest_b.id)
            if "error" in proposal or not proposal.get("cut_edges"):
                break
            for edge in proposal["cut_edges"]:
                dep = session.exec(
                    select(TaskDep).where(
                        TaskDep.task_id == edge["task_id"],
                        TaskDep.depends_on_task_id == edge["depends_on_task_id"],
                    )
                ).first()
                if dep:
                    dep.kind = "handoff"
                    session.add(dep)
            session.flush()
            blocks = bundle(session, project_id)
            tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()

    task_by_block = defaultdict(list)
    for t in tasks:
        if t.block_id:
            task_by_block[t.block_id].append(t)

    total_weight = sum(b.total_effort or 0 for b in blocks)
    fair_share = total_weight / n_members if n_members > 0 else 0

    member_loads: dict[int, int] = {m.id: 0 for m in members}
    oversize_warnings: list[str] = []

    if n_members == 1:
        solo_member = members[0]
        for b in blocks:
            b.owner_member_id = solo_member.id
            b.oversize_flag = False
            session.add(b)
            member_loads[solo_member.id] += b.total_effort or 0
            for t in task_by_block[b.id]:
                t.owner_member_id = solo_member.id
                session.add(t)

        for t in tasks:
            if t.is_milestone:
                t.owner_member_id = solo_member.id
                session.add(t)

        session.flush()
        return {
            "blocks": blocks,
            "loads": member_loads,
            "oversize_warnings": [],
        }

    sorted_blocks = sorted(blocks, key=lambda b: (b.total_effort or 0, -(b.id or 0)), reverse=True)

    for b in sorted_blocks:
        b_effort = b.total_effort or 0
        if b_effort > 1.4 * fair_share:
            b.oversize_flag = True
            oversize_warnings.append(
                f"Block '{b.name}' ({b_effort} pts) exceeds 1.4x fair share ({fair_share:.1f} pts)"
            )
        else:
            b.oversize_flag = False

        block_text = f"{b.name} " + " ".join(f"{t.title} {t.description or ''}" for t in task_by_block[b.id])

        best_member = min(
            members,
            key=lambda m: (
                member_loads[m.id],
                -token_overlap(block_text, getattr(m, "skills", None) or getattr(m, "role", None) or ""),
                m.id,
            ),
        )

        b.owner_member_id = best_member.id
        member_loads[best_member.id] += b_effort
        session.add(b)

        for t in task_by_block[b.id]:
            t.owner_member_id = best_member.id
            session.add(t)

    lead_member = next((m for m in members if m.role == "lead"), members[0])
    for t in tasks:
        if t.is_milestone:
            t.owner_member_id = lead_member.id
            session.add(t)

    session.flush()
    return {
        "blocks": sorted_blocks,
        "loads": member_loads,
        "oversize_warnings": oversize_warnings,
    }


def confirm_assignment(session: Session, project_id: int) -> dict[str, Any]:
    blocks = session.exec(select(Block).where(Block.project_id == project_id)).all()
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()

    add_event(
        session=session,
        project_id=project_id,
        type="tasks_bundled",
        payload={"block_count": len(blocks), "task_count": len(tasks)},
    )

    for b in blocks:
        add_event(
            session=session,
            project_id=project_id,
            type="block_assigned",
            actor_member_id=b.owner_member_id,
            payload={
                "block_id": b.id,
                "block_name": b.name,
                "owner_member_id": b.owner_member_id,
                "total_effort": b.total_effort,
                "oversize_flag": b.oversize_flag,
            },
        )

    compute_deadlines(session, project_id)
    session.flush()
    return {"status": "confirmed", "block_count": len(blocks)}



def apply_split(session: Session, block_id: int) -> dict[str, Any]:
    proposal = propose_split(session, block_id)
    if "error" in proposal:
        return proposal

    block = session.get(Block, block_id)
    project_id = block.project_id

    for edge in proposal["cut_edges"]:
        dep = session.exec(
            select(TaskDep).where(
                TaskDep.task_id == edge["task_id"],
                TaskDep.depends_on_task_id == edge["depends_on_task_id"],
            )
        ).first()
        if dep:
            dep.kind = "handoff"
            session.add(dep)

    session.flush()
    bundle(session, project_id)
    assign(session, project_id)
    compute_deadlines(session, project_id)
    return {"status": "split_applied", "block_id": block_id}


def compute_deadlines(session: Session, project_id: int) -> list[Task]:
    project = session.get(Project, project_id)
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    if not tasks or not project:
        return []

    now = datetime.now(timezone.utc)
    if settings.DEMO_MODE:
        starts_at = project.starts_at or now
        ends_at = starts_at + timedelta(minutes=40)
    else:
        starts_at = project.starts_at or now
        ends_at = project.ends_at or (starts_at + timedelta(hours=20))

    project.starts_at = starts_at
    project.ends_at = ends_at
    session.add(project)

    window_delta = ends_at - starts_at
    work_end = ends_at - timedelta(seconds=0.1 * window_delta.total_seconds())

    blocks = session.exec(select(Block).where(Block.project_id == project_id)).all()
    deps = session.exec(select(TaskDep)).all()

    for b in blocks:
        b_tasks = [t for t in tasks if t.block_id == b.id]
        if not b_tasks:
            continue

        b_ids = {t.id for t in b_tasks}
        b_deps = [d for d in deps if d.task_id in b_ids and d.depends_on_task_id in b_ids]
        ordered_b_tasks = topological_sort(b_tasks, b_deps)

        total_b_effort = sum(t.effort or 1 for t in ordered_b_tasks)
        cumulative_effort = 0

        for t in ordered_b_tasks:
            cumulative_effort += (t.effort or 1)
            ratio = cumulative_effort / total_b_effort if total_b_effort > 0 else 1.0
            task_deadline = starts_at + timedelta(seconds=ratio * (work_end - starts_at).total_seconds())
            t.deadline = task_deadline
            session.add(t)

    for t in tasks:
        if t.is_milestone:
            t.deadline = ends_at
            session.add(t)

    session.flush()
    return tasks
