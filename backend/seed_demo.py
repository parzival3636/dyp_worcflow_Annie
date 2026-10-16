"""
Pilot – seed demo data.

Creates a project with 4 members and Kabir's "Connect the payment API" task.
Run: python seed_demo.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from db import get_session
from models import Block, Event, Member, Project, Task


def seed():
    """Create the demo project with 4 members and tasks."""
    with get_session() as session:
        # Check if demo project already exists
        from sqlmodel import select
        existing = session.exec(
            select(Project).where(Project.code == "demo01")
        ).first()
        if existing:
            print(f"Demo project already exists (id={existing.id}). Skipping.")
            return existing.id

        now = datetime.now(timezone.utc)

        # Create project
        project = Project(
            code="demo01",
            name="PayFlow",
            idea="A payment processing app for campus events",
            repo_full_name="pilot-team/payflow",
            repo_url="https://github.com/pilot-team/payflow",
            status="running",
            starts_at=now,
            ends_at=now + timedelta(hours=48),
        )
        session.add(project)
        session.flush()

        # Create 4 members (telegram_id must be set to real IDs for live testing)
        kabir = Member(
            project_id=project.id,
            name="Kabir",
            telegram_id=0,  # Replace with real Telegram ID for testing
            telegram_username="kabir_dev",
            github_login="kabir-dev",
            role="lead",
            invite_status="accepted",
            onboarding_state="done",
            aliases=["kabir", "kabs", "bhai"],
        )
        session.add(kabir)
        session.flush()

        project.lead_member_id = kabir.id
        session.add(project)

        meera = Member(
            project_id=project.id,
            name="Meera",
            telegram_id=0,  # Replace with real Telegram ID
            telegram_username="meera_codes",
            github_login="meera-codes",
            role="member",
            invite_status="accepted",
            onboarding_state="done",
            aliases=["meera", "mee"],
        )
        session.add(meera)
        session.flush()

        arjun = Member(
            project_id=project.id,
            name="Arjun",
            telegram_id=0,
            telegram_username="arjun_py",
            github_login="arjun-py",
            role="member",
            invite_status="accepted",
            onboarding_state="done",
            aliases=["arjun", "aj"],
        )
        session.add(arjun)
        session.flush()

        priya = Member(
            project_id=project.id,
            name="Priya",
            telegram_id=0,
            telegram_username="priya_ui",
            github_login="priya-ui",
            role="member",
            invite_status="accepted",
            onboarding_state="done",
            aliases=["priya", "pri"],
        )
        session.add(priya)
        session.flush()

        # Create block
        block = Block(
            project_id=project.id,
            name="Backend Integration",
            total_effort=8,
            owner_member_id=kabir.id,
        )
        session.add(block)
        session.flush()

        # Create tasks
        # T-1: Kabir's payment API task (the PS example)
        t1 = Task(
            project_id=project.id,
            key="T-1",
            title="Connect the payment API",
            description="Integrate the Razorpay payment gateway API for event ticket purchases",
            acceptance_criteria=[
                "Payment endpoint responds to POST /pay",
                "Test transactions pass in sandbox mode",
                "Error handling for failed transactions",
            ],
            effort=3,
            status="todo",
            block_id=block.id,
            owner_member_id=kabir.id,
            deadline=now + timedelta(hours=24),
        )
        session.add(t1)

        # T-2: Meera's frontend
        t2 = Task(
            project_id=project.id,
            key="T-2",
            title="Build the event listing page",
            description="Create a responsive page showing upcoming campus events with filters",
            acceptance_criteria=[
                "Events displayed in a grid/list",
                "Filter by date, category",
                "Mobile responsive",
            ],
            effort=2,
            status="in_progress",
            owner_member_id=meera.id,
            deadline=now + timedelta(hours=20),
            started_at=now - timedelta(hours=2),
            progress=30,
        )
        session.add(t2)

        # T-3: Arjun's auth
        t3 = Task(
            project_id=project.id,
            key="T-3",
            title="Set up user authentication",
            description="Implement JWT-based auth with login/signup endpoints",
            acceptance_criteria=[
                "POST /auth/login and /auth/signup work",
                "JWT tokens issued and validated",
                "Password hashing with bcrypt",
            ],
            effort=3,
            status="todo",
            owner_member_id=arjun.id,
            deadline=now + timedelta(hours=18),
        )
        session.add(t3)

        # T-4: Priya's dashboard
        t4 = Task(
            project_id=project.id,
            key="T-4",
            title="Design the admin dashboard",
            description="Create the admin panel for managing events and viewing analytics",
            acceptance_criteria=[
                "Dashboard shows event stats",
                "CRUD for events",
                "Export analytics as CSV",
            ],
            effort=2,
            status="todo",
            owner_member_id=priya.id,
            deadline=now + timedelta(hours=30),
        )
        session.add(t4)

        # Event
        event = Event(
            project_id=project.id,
            ts=now,
            type="project_created",
            payload={"seeded": True, "demo": True},
        )
        session.add(event)

        print(f"[OK] Demo project seeded:")
        print(f"   Project: {project.name} (code: {project.code})")
        print(f"   Members: Kabir (lead), Meera, Arjun, Priya")
        print(f"   Tasks: T-1 (Kabir), T-2 (Meera), T-3 (Arjun), T-4 (Priya)")
        print(f"\n[!] Set real Telegram IDs in the member rows for live testing!")
        print(f"   Kabir id: {kabir.id}, Meera id: {meera.id}, Arjun id: {arjun.id}, Priya id: {priya.id}")

        return project.id


if __name__ == "__main__":
    seed()
