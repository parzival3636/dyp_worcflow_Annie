from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
import pytest

from backend.config import settings
from backend.models import Project, Member, Block, Task, TaskDep
from backend.llm import P2Task, P2Plan
import backend.planner as planner_module
from backend.planner import (
    sanitize_task_titles,
    prune_unknown_deps,
    remove_dependency_cycles,
    ensure_milestone,
    validate_and_sanitize_tasks,
    generate_plan,
    bundle,
    assign,
    confirm_assignment,
    propose_split,
    apply_split,
    compute_deadlines,
)


def test_p1_duplicate_titles():
    raw = [
        P2Task(title="Build Auth", description="d", acceptance_criteria=["c"], effort=3),
        P2Task(title="Build Auth", description="d", acceptance_criteria=["c"], effort=2),
        P2Task(title="Build Auth", description="d", acceptance_criteria=["c"], effort=1),
    ]
    sanitized = sanitize_task_titles(raw)
    titles = [t.title for t in sanitized]
    assert titles == ["Build Auth", "Build Auth (2)", "Build Auth (3)"]


def test_p2_unknown_deps_pruned():
    raw = [
        P2Task(title="Task A", description="d", acceptance_criteria=["c"], effort=2, depends_on=["Nonexistent Task"]),
        P2Task(title="Task B", description="d", acceptance_criteria=["c"], effort=3, depends_on=["Task A"]),
    ]
    pruned = prune_unknown_deps(raw)
    assert pruned[0].depends_on == []
    assert pruned[1].depends_on == ["Task A"]


def test_p3_cycle_detection_and_removal():
    raw = [
        P2Task(title="A", description="d", acceptance_criteria=["c"], effort=1, depends_on=["C"]),
        P2Task(title="B", description="d", acceptance_criteria=["c"], effort=1, depends_on=["A"]),
        P2Task(title="C", description="d", acceptance_criteria=["c"], effort=1, depends_on=["B"]),
    ]
    acyclic = remove_dependency_cycles(raw)
    # Check that at least one edge was dropped so there's no cycle
    # Trace graph to verify no cycle
    adj = {t.title: t.depends_on for t in acyclic}
    visited = set()
    stack = set()

    def has_cycle(node):
        visited.add(node)
        stack.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in stack:
                return True
        stack.remove(node)
        return False

    assert not any(has_cycle(node) for node in adj if node not in visited)


def test_p4_no_milestone_marks_last_as_milestone():
    raw = [
        P2Task(title="Task 1", description="d", acceptance_criteria=["c"], effort=2, is_milestone=False),
        P2Task(title="Final Presentation", description="d", acceptance_criteria=["c"], effort=3, is_milestone=False),
    ]
    result = ensure_milestone(raw)
    assert result[-1].is_milestone is True
    assert "Demo" in result[-1].title or "Presentation" in result[-1].title


def test_p5_keys_exactly_t1_to_tn_no_gaps(session: Session, sample_project: Project, monkeypatch):
    mock_p2_tasks = [
        P2Task(title=f"Task {i}", description="desc", acceptance_criteria=["ac"], effort=2)
        for i in range(1, 15)
    ]
    monkeypatch.setattr(
        planner_module,
        "call_json",
        lambda *args, **kwargs: P2Plan(tasks=mock_p2_tasks),
    )

    tasks = generate_plan(session, sample_project.id, idea="Test Idea")
    assert len(tasks) == 14
    for idx, t in enumerate(tasks, start=1):
        assert t.key == f"T-{idx}"


def test_p6_bundle_chain_plus_isolated(session: Session, sample_project: Project):
    # 3 chained tasks (T1 -> T2 -> T3) and 2 isolated tasks (T4, T5)
    t1 = Task(project_id=sample_project.id, key="T-1", title="T1", effort=2)
    t2 = Task(project_id=sample_project.id, key="T-2", title="T2", effort=3)
    t3 = Task(project_id=sample_project.id, key="T-3", title="T3", effort=4)
    t4 = Task(project_id=sample_project.id, key="T-4", title="T4", effort=2)
    t5 = Task(project_id=sample_project.id, key="T-5", title="T5", effort=1)
    session.add_all([t1, t2, t3, t4, t5])
    session.commit()

    # Hard deps: T2 depends on T1, T3 depends on T2
    d1 = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="hard")
    d2 = TaskDep(task_id=t3.id, depends_on_task_id=t2.id, kind="hard")
    session.add_all([d1, d2])
    session.commit()

    blocks = bundle(session, sample_project.id)
    # T1, T2, T3 form 1 block. T4 forms 1 block. T5 forms 1 block. Total = 3 blocks.
    assert len(blocks) == 3


def test_p7_handoff_edges_ignored_in_bundling(session: Session, sample_project: Project):
    t1 = Task(project_id=sample_project.id, key="T-1", title="Backend API", effort=3)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Frontend UI", effort=3)
    session.add_all([t1, t2])
    session.commit()

    # Handoff edge: T2 depends on T1 with kind='handoff'
    dep = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="handoff")
    session.add(dep)
    session.commit()

    blocks = bundle(session, sample_project.id)
    # Should be in 2 separate blocks because handoff edges are not bundled
    assert len(blocks) == 2


def test_p8_milestones_excluded_from_blocks(session: Session, sample_project: Project):
    t1 = Task(project_id=sample_project.id, key="T-1", title="Normal Task", effort=2, is_milestone=False)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Demo Milestone", effort=1, is_milestone=True)
    session.add_all([t1, t2])
    session.commit()

    blocks = bundle(session, sample_project.id)
    session.refresh(t1)
    session.refresh(t2)

    assert len(blocks) == 1
    assert t1.block_id == blocks[0].id
    assert t2.block_id is None


def test_p9_assignment_four_equal_blocks_four_members(session: Session, sample_project: Project):
    members = [
        Member(project_id=sample_project.id, name=f"Member {i}", role="member", skills="python")
        for i in range(1, 5)
    ]
    session.add_all(members)
    session.commit()

    tasks = [
        Task(project_id=sample_project.id, key=f"T-{i}", title=f"Task {i}", effort=3)
        for i in range(1, 5)
    ]
    session.add_all(tasks)
    session.commit()

    blocks = bundle(session, sample_project.id)
    assert len(blocks) == 4

    preview = assign(session, sample_project.id)
    loads = preview["loads"]
    # 4 equal blocks (3 pts each) assigned across 4 members -> 1 block each (3 pts load each)
    for m in members:
        assert loads[m.id] == 3


def test_p10_assignment_tie_break_by_skill(session: Session, sample_project: Project):
    m1 = Member(project_id=sample_project.id, name="Alice", skills="react css frontend")
    m2 = Member(project_id=sample_project.id, name="Bob", skills="docker devops kubernetes")
    session.add_all([m1, m2])
    session.commit()

    t = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Deploy Kubernetes Docker Cluster",
        description="Setup devops pipeline",
        effort=5,
    )
    session.add(t)
    session.commit()

    bundle(session, sample_project.id)
    assign(session, sample_project.id)

    block = session.exec(select(Block).where(Block.project_id == sample_project.id)).first()
    # Bob has matching skills, so should be assigned despite equal 0 load
    assert block.owner_member_id == m2.id


def test_p11_heavy_block_oversize_flag(session: Session, sample_project: Project):
    m1 = Member(project_id=sample_project.id, name="A")
    m2 = Member(project_id=sample_project.id, name="B")
    session.add_all([m1, m2])
    session.commit()

    # Block 1 effort = 15, Block 2 effort = 3. Total = 18. Fair share = 9.
    # 15 > 1.4 * 9 (12.6) -> oversize_flag should be True
    t1 = Task(project_id=sample_project.id, key="T-1", title="Massive Block", effort=15)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Small Block", effort=3)
    session.add_all([t1, t2])
    session.commit()

    bundle(session, sample_project.id)
    assign(session, sample_project.id)

    b1 = session.exec(select(Block).where(Block.total_effort == 15)).first()
    assert b1.oversize_flag is True


def test_p12_split_proposal_and_apply(session: Session, sample_project: Project):
    m1 = Member(project_id=sample_project.id, name="M1")
    session.add(m1)
    session.commit()

    # Chain of 4 tasks of efforts 2, 2, 2, 2
    t1 = Task(project_id=sample_project.id, key="T-1", title="Step 1", effort=2)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Step 2", effort=2)
    t3 = Task(project_id=sample_project.id, key="T-3", title="Step 3", effort=2)
    t4 = Task(project_id=sample_project.id, key="T-4", title="Step 4", effort=2)
    session.add_all([t1, t2, t3, t4])
    session.commit()

    d1 = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="hard")
    d2 = TaskDep(task_id=t3.id, depends_on_task_id=t2.id, kind="hard")
    d3 = TaskDep(task_id=t4.id, depends_on_task_id=t3.id, kind="hard")
    session.add_all([d1, d2, d3])
    session.commit()

    blocks = bundle(session, sample_project.id)
    assert len(blocks) == 1
    block_id = blocks[0].id

    # Propose split
    proposal = propose_split(session, block_id)
    assert proposal["imbalance"] == 0  # 4 and 4
    assert len(proposal["left_tasks"]) == 2
    assert len(proposal["right_tasks"]) == 2

    # Apply split: changes the cut edge to handoff and splits into 2 blocks
    apply_split(session, block_id)
    new_blocks = session.exec(select(Block).where(Block.project_id == sample_project.id)).all()
    assert len(new_blocks) == 2


def test_p13_single_member_no_oversize(session: Session, sample_project: Project):
    solo = Member(project_id=sample_project.id, name="Solo Hacker")
    session.add(solo)
    session.commit()

    t1 = Task(project_id=sample_project.id, key="T-1", title="Massive Task", effort=20)
    session.add(t1)
    session.commit()

    bundle(session, sample_project.id)
    preview = assign(session, sample_project.id)

    assert len(preview["oversize_warnings"]) == 0
    block = session.exec(select(Block).where(Block.project_id == sample_project.id)).first()
    assert block.oversize_flag is False
    assert block.owner_member_id == solo.id


def test_p14_monotonic_deadlines(session: Session, sample_project: Project):
    t1 = Task(project_id=sample_project.id, key="T-1", title="First", effort=3)
    t2 = Task(project_id=sample_project.id, key="T-2", title="Second", effort=5)
    t3 = Task(project_id=sample_project.id, key="T-3", title="Final Milestone", effort=1, is_milestone=True)
    session.add_all([t1, t2, t3])
    session.commit()

    d1 = TaskDep(task_id=t2.id, depends_on_task_id=t1.id, kind="hard")
    session.add(d1)
    session.commit()

    bundle(session, sample_project.id)
    tasks = compute_deadlines(session, sample_project.id)

    task_map = {t.key: t for t in tasks}
    assert task_map["T-1"].deadline < task_map["T-2"].deadline
    assert task_map["T-2"].deadline <= task_map["T-3"].deadline
    assert task_map["T-3"].deadline == sample_project.ends_at


def test_p15_demo_mode_window_between_30_and_45_min(session: Session, sample_project: Project, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)

    t1 = Task(project_id=sample_project.id, key="T-1", title="Fast Task", effort=2)
    session.add(t1)
    session.commit()

    bundle(session, sample_project.id)
    compute_deadlines(session, sample_project.id)
    session.refresh(sample_project)

    duration_minutes = (sample_project.ends_at - sample_project.starts_at).total_seconds() / 60
    assert 30 <= duration_minutes <= 45


def test_p16_rebundle_is_idempotent(session: Session, sample_project: Project):
    t1 = Task(project_id=sample_project.id, key="T-1", title="A", effort=2)
    t2 = Task(project_id=sample_project.id, key="T-2", title="B", effort=2)
    session.add_all([t1, t2])
    session.commit()

    b1 = bundle(session, sample_project.id)
    assert len(b1) == 2

    # Second bundle call
    b2 = bundle(session, sample_project.id)
    assert len(b2) == 2

    all_blocks = session.exec(select(Block).where(Block.project_id == sample_project.id)).all()
    assert len(all_blocks) == 2


def test_p17_random_dag_bundling_property(session: Session, sample_project: Project):
    # Property: Every non-milestone task is in exactly one block, and no hard edge crosses blocks
    tasks = [
        Task(project_id=sample_project.id, key=f"T-{i}", title=f"Node {i}", effort=i % 4 + 1)
        for i in range(1, 10)
    ]
    tasks[-1].is_milestone = True
    session.add_all(tasks)
    session.commit()

    # Create several hard edges
    deps = [
        TaskDep(task_id=tasks[1].id, depends_on_task_id=tasks[0].id, kind="hard"),
        TaskDep(task_id=tasks[2].id, depends_on_task_id=tasks[1].id, kind="hard"),
        TaskDep(task_id=tasks[4].id, depends_on_task_id=tasks[3].id, kind="hard"),
        TaskDep(task_id=tasks[6].id, depends_on_task_id=tasks[5].id, kind="hard"),
        TaskDep(task_id=tasks[7].id, depends_on_task_id=tasks[6].id, kind="hard"),
    ]
    session.add_all(deps)
    session.commit()

    blocks = bundle(session, sample_project.id)
    refreshed_tasks = session.exec(select(Task).where(Task.project_id == sample_project.id)).all()

    # Property 1: Non-milestones must have block_id assigned
    for t in refreshed_tasks:
        if not t.is_milestone:
            assert t.block_id is not None
        else:
            assert t.block_id is None

    # Property 2: No hard edge crosses blocks
    task_block_map = {t.id: t.block_id for t in refreshed_tasks if not t.is_milestone}
    for d in deps:
        if d.task_id in task_block_map and d.depends_on_task_id in task_block_map:
            assert task_block_map[d.task_id] == task_block_map[d.depends_on_task_id]
