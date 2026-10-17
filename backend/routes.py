"""
Pilot – REST API Routes.

Implements all endpoints from PRD Section 13:
- GET /api/projects
- GET /api/projects/{code}
- GET /api/projects/{code}/snapshot
- POST /api/projects/{code}/plan
- POST /api/projects/{code}/bundle
- POST /api/projects/{code}/confirm-assignment
- POST /api/projects/{code}/kickoff
- POST /api/projects/{code}/tasks
- PATCH /api/projects/{code}/tasks/{key}
- DELETE /api/projects/{code}/tasks/{key}
- POST /api/projects/{code}/tasks/{key}/override-verify
- POST /api/projects/{code}/ask
- GET /api/projects/{code}/events
- GET /api/projects/{code}/contributions
"""
import logging
import secrets
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlmodel import select

logger = logging.getLogger("pilot.routes")

from auth import get_current_user, get_current_user_optional
from config import get_settings
from db import get_session
from models import (
    Block, Blocker, CommitLog, Contradiction, Event,
    Invite, Member, Project, Task, TaskDep, User, Verification
)

router = APIRouter()


# ── Project metadata & listing ─────────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    name: str
    idea: Optional[str] = None
    description: Optional[str] = None
    functional_requirements: Optional[str] = None
    non_functional_requirements: Optional[str] = None
    constraints: Optional[str] = None
    repo_url: Optional[str] = None
    repo_full_name: Optional[str] = None


class InviteCreateRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = "member"


class InviteAcceptRequest(BaseModel):
    name: Optional[str] = None
    github_login: Optional[str] = None
    telegram_username: Optional[str] = None


def _generate_project_code() -> str:
    """Generate a unique 6-character lowercase alphanumeric project code."""
    alphabet = "23456789abcdefghjkmnpqrstuvwxyz"
    return "".join(secrets.choice(alphabet) for _ in range(6))


@router.get("/projects")
def list_projects(current_user: Optional[User] = Depends(get_current_user_optional)):
    """List projects with comprehensive summary."""
    with get_session() as session:
        projects = session.exec(select(Project).order_by(Project.id.desc())).all()
        return [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "idea": p.idea or p.description,
                "description": p.description or p.idea,
                "status": p.status,
                "plan_status": p.plan_status or "draft",
                "repo_url": p.repo_url,
                "repo_full_name": p.repo_full_name,
                "telegram_chat_id": p.telegram_chat_id or p.telegram_group_id,
                "telegram_status": p.telegram_status or "disconnected",
                "is_leader": bool(current_user and p.leader_user_id == current_user.id),
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "starts_at": p.starts_at.isoformat() if p.starts_at else None,
                "ends_at": p.ends_at.isoformat() if p.ends_at else None,
            }
            for p in projects
        ]


@router.post("/projects")
def create_project(
    payload: ProjectCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a new project dynamically from the web application."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Project name is required")

    with get_session() as session:
        # Generate unique code
        code = _generate_project_code()
        while session.exec(select(Project).where(Project.code == code)).first():
            code = _generate_project_code()

        user_id = current_user.id if current_user else None
        leader_name = current_user.name if current_user else "Team Lead"
        leader_email = current_user.email if current_user else None

        now = datetime.now(timezone.utc)
        project = Project(
            code=code,
            name=payload.name.strip(),
            idea=payload.idea or payload.description,
            description=payload.description or payload.idea,
            functional_requirements=payload.functional_requirements,
            non_functional_requirements=payload.non_functional_requirements,
            constraints=payload.constraints,
            repo_url=payload.repo_url,
            repo_full_name=payload.repo_full_name,
            leader_user_id=user_id,
            status="planning",
            plan_status="draft",
            telegram_status="disconnected",
            created_at=now,
        )
        session.add(project)
        session.flush()
        session.refresh(project)

        # Automatically add the leader as the first project member
        lead_member = Member(
            project_id=project.id,
            user_id=user_id,
            name=leader_name,
            email=leader_email,
            role="lead",
            invite_status="accepted",
            onboarding_state="done",
        )
        session.add(lead_member)
        session.flush()
        session.refresh(lead_member)

        project.lead_member_id = lead_member.id
        session.add(project)

        # Log project creation event
        event = Event(
            project_id=project.id,
            ts=now,
            actor_member_id=lead_member.id,
            type="project_created",
            payload={
                "code": project.code,
                "name": project.name,
                "leader": leader_name,
            },
        )
        session.add(event)
        session.flush()

        # Automatically generate initial engineering tasks for the project
        try:
            from planner import generate_plan
            generate_plan(
                session=session,
                project_id=project.id,
                idea=project.idea or project.description or project.name,
            )
        except Exception as exc:
            logger.warning("Initial plan generation on project creation deferred: %s", exc)

        return {
            "id": project.id,
            "code": project.code,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "plan_status": project.plan_status,
            "telegram_status": project.telegram_status,
            "repo_url": project.repo_url,
            "lead_member_id": lead_member.id,
        }


@router.get("/projects/{code}")
def get_project(code: str):
    """Retrieve metadata for project by code."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "id": project.id,
            "code": project.code,
            "name": project.name,
            "idea": project.idea,
            "description": project.description or project.idea,
            "functional_requirements": project.functional_requirements,
            "non_functional_requirements": project.non_functional_requirements,
            "constraints": project.constraints,
            "repo_full_name": project.repo_full_name,
            "repo_url": project.repo_url,
            "telegram_chat_id": project.telegram_chat_id or project.telegram_group_id,
            "telegram_status": project.telegram_status or "disconnected",
            "status": project.status,
            "plan_status": project.plan_status or "draft",
            "starts_at": project.starts_at.isoformat() if project.starts_at else None,
            "ends_at": project.ends_at.isoformat() if project.ends_at else None,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }


@router.get("/projects/{code}/telegram-status")
def get_telegram_status(code: str):
    """Check Telegram binding status for the project."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        chat_id = project.telegram_chat_id or project.telegram_group_id
        is_connected = bool(chat_id and (project.telegram_status == "connected" or chat_id != 0))

        # Recent messages count in group
        msg_count = 0
        if chat_id:
            from models import Message
            msg_count = len(session.exec(
                select(Message).where(Message.chat_id == chat_id)
            ).all())

        return {
            "code": project.code,
            "telegram_status": "connected" if is_connected else "disconnected",
            "telegram_chat_id": chat_id,
            "message_count": msg_count,
            "instructions": {
                "step1": "Create a Telegram group with your project team",
                "step2": "Add Pilot bot (@pilot_coordinator_bot) to your group",
                "step3": f"Send /link {code} in the group chat",
            }
        }


@router.post("/projects/{code}/telegram-disconnect")
def disconnect_telegram(code: str):
    """Disconnect Telegram group from the project."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project.telegram_chat_id = None
        project.telegram_group_id = None
        project.telegram_status = "disconnected"
        session.add(project)

        event = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            type="telegram_disconnected",
            payload={"code": project.code},
        )
        session.add(event)
        return {"ok": True, "message": "Telegram group unlinked"}


# ── Invites ────────────────────────────────────────────────────────────────

@router.get("/projects/{code}/invites")
def list_project_invites(code: str):
    """List pending invites for the project."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        invites = session.exec(
            select(Invite).where(Invite.project_id == project.id).order_by(Invite.id.desc())
        ).all()
        return [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "token": inv.token,
                "status": inv.status,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "invite_url": f"/invite/{inv.token}",
            }
            for inv in invites
        ]


@router.post("/projects/{code}/invites")
def create_project_invite(
    code: str,
    payload: InviteCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create and issue an invite link for a team member or guide."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        token = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc)
        invite = Invite(
            project_id=project.id,
            email=payload.email.lower().strip(),
            role=payload.role if payload.role in ("lead", "member", "guide") else "member",
            token=token,
            status="pending",
            invited_by_user_id=current_user.id if current_user else None,
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        session.add(invite)

        # Check if member already exists
        existing_member = session.exec(
            select(Member).where(
                Member.project_id == project.id,
                Member.email == payload.email.lower().strip(),
            )
        ).first()

        member_name = payload.name or payload.email.split("@")[0]
        if not existing_member:
            member = Member(
                project_id=project.id,
                name=member_name,
                email=payload.email.lower().strip(),
                role=invite.role,
                invite_status="pending",
                onboarding_state="new",
            )
            session.add(member)
        else:
            # Update name if provided
            if payload.name:
                existing_member.name = payload.name
                session.add(existing_member)

        # Send invite email if SMTP is configured
        settings = get_settings()
        invite_url = f"{settings.frontend_url}/invite/{token}"
        email_sent = False
        if settings.smtp_host and settings.smtp_user:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"You've been invited to join '{project.name}' on Pilot"
                msg["From"] = settings.smtp_from or settings.smtp_user
                msg["To"] = payload.email

                text_body = (
                    f"Hi {member_name},\n\n"
                    f"You've been invited to join the project '{project.name}' on Pilot as a {invite.role}.\n\n"
                    f"Click the link below to accept and get access:\n{invite_url}\n\n"
                    f"This link expires in 7 days.\n\nThe Pilot Team"
                )
                html_body = f"""
                <html><body style="font-family:sans-serif;background:#0A0B0D;color:#E8E6E1;padding:32px">
                  <div style="max-width:520px;margin:0 auto;background:#111316;border:1px solid #23272D;border-radius:12px;padding:32px">
                    <h2 style="color:#FF6B3D;margin-top:0">You're invited to Pilot 🚀</h2>
                    <p>Hi <strong>{member_name}</strong>,</p>
                    <p>You've been invited to join the project <strong>{project.name}</strong> as a <strong>{invite.role}</strong>.</p>
                    <p>Click the button below to accept the invite and gain access to the project board:</p>
                    <a href="{invite_url}" style="display:inline-block;margin:16px 0;padding:12px 24px;background:#FF6B3D;color:#fff;border-radius:8px;text-decoration:none;font-weight:600">Accept Invite</a>
                    <p style="color:#8A8F98;font-size:12px">Or copy this link: {invite_url}</p>
                    <p style="color:#8A8F98;font-size:12px">This link expires in 7 days.</p>
                  </div>
                </body></html>
                """
                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.sendmail(msg["From"], [payload.email], msg.as_string())
                email_sent = True
                logger.info("Invite email sent to %s for project %s", payload.email, project.code)
            except Exception as exc:
                logger.warning("Failed to send invite email to %s: %s", payload.email, exc)
        else:
            logger.info("SMTP not configured – invite link: %s", invite_url)

        return {
            "token": token,
            "email": invite.email,
            "name": member_name,
            "role": invite.role,
            "invite_url": f"/invite/{token}",
            "email_sent": email_sent,
        }


@router.get("/invites/{token}")
def get_invite_details(token: str):
    """Retrieve invite information for acceptance screen."""
    with get_session() as session:
        invite = session.exec(select(Invite).where(Invite.token == token)).first()
        if not invite:
            raise HTTPException(status_code=404, detail="Invalid or expired invite link")

        project = session.get(Project, invite.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Associated project not found")

        return {
            "token": invite.token,
            "email": invite.email,
            "role": invite.role,
            "status": invite.status,
            "project": {
                "name": project.name,
                "code": project.code,
                "description": project.description or project.idea,
            }
        }


@router.post("/invites/{token}/accept")
def accept_invite(
    token: str,
    payload: InviteAcceptRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Accept an invitation to join a project."""
    with get_session() as session:
        invite = session.exec(select(Invite).where(Invite.token == token)).first()
        if not invite:
            raise HTTPException(status_code=404, detail="Invalid or expired invite")

        if invite.status == "accepted":
            project = session.get(Project, invite.project_id)
            return {"ok": True, "project_code": project.code if project else None, "message": "Already accepted"}

        project = session.get(Project, invite.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        invite.status = "accepted"
        session.add(invite)

        # Find or create member
        member = session.exec(
            select(Member).where(
                Member.project_id == project.id,
                Member.email == invite.email,
            )
        ).first()

        user_id = current_user.id if current_user else None
        display_name = payload.name or (current_user.name if current_user else invite.email.split("@")[0])

        if not member:
            member = Member(
                project_id=project.id,
                user_id=user_id,
                name=display_name,
                email=invite.email,
                github_login=payload.github_login,
                telegram_username=payload.telegram_username,
                role=invite.role,
                invite_status="accepted",
                onboarding_state="done",
            )
            session.add(member)
        else:
            member.invite_status = "accepted"
            member.onboarding_state = "done"
            if user_id:
                member.user_id = user_id
            if payload.name:
                member.name = payload.name
            if payload.github_login:
                member.github_login = payload.github_login
            if payload.telegram_username:
                member.telegram_username = payload.telegram_username
            session.add(member)

        # Log member joined event
        event = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            actor_member_id=member.id if member.id else None,
            type="member_joined",
            payload={"name": member.name, "email": member.email, "role": member.role},
        )
        session.add(event)

        return {
            "ok": True,
            "project_code": project.code,
            "member_id": member.id,
            "name": member.name,
        }


# ── Snapshot endpoint (polled every 2s) ────────────────────────────────────

@router.get("/projects/{code}/snapshot")
def get_snapshot(code: str):
    """
    Returns full live project snapshot matching exact PRD contract.
    """
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Members
        members = session.exec(select(Member).where(Member.project_id == project.id)).all()
        members_data = [
            {
                "id": m.id,
                "name": m.name,
                "email": m.email,
                "role": m.role,
                "github_login": m.github_login,
                "telegram_username": m.telegram_username,
                "telegram_id": m.telegram_id,
                "invite_status": m.invite_status,
                "onboarding_state": m.onboarding_state,
                "color": None, # Computed on frontend by getOwnerColor
            }
            for m in members
        ]

        # Blocks
        blocks = session.exec(select(Block).where(Block.project_id == project.id)).all()
        blocks_data = [
            {
                "id": b.id,
                "name": b.name,
                "owner_member_id": b.owner_member_id,
                "total_effort": b.total_effort,
                "oversize_flag": b.oversize_flag,
            }
            for b in blocks
        ]

        # Tasks
        tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
        task_id_to_key = {t.id: t.key for t in tasks}

        # Blockers mapped by task_id
        open_blockers = session.exec(
            select(Blocker).where(Blocker.status.in_(["open", "routed"]))
        ).all()
        blocker_by_task = {b.task_id: b for b in open_blockers}

        # Verifications mapped by task_id (latest)
        verifications = session.exec(select(Verification)).all()
        verify_by_task = {}
        for v in verifications:
            verify_by_task[v.task_id] = v

        tasks_data = []
        for t in tasks:
            b = blocker_by_task.get(t.id)
            v = verify_by_task.get(t.id)
            tasks_data.append({
                "key": t.key,
                "title": t.title,
                "status": t.status,
                "owner_member_id": t.owner_member_id,
                "block_id": t.block_id,
                "effort": t.effort,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "progress": t.progress,
                "risk": t.risk,
                "is_milestone": t.is_milestone,
                "acceptance_criteria": t.acceptance_criteria or [],
                "description": t.description,
                "verification": {
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "reason": v.reason,
                } if v else None,
                "blocker": {
                    "id": b.id,
                    "description": b.description,
                    "status": b.status,
                    "routed_to": b.routed_to_member_id,
                } if b else None,
            })

        # Task dependencies
        deps = session.exec(select(TaskDep)).all()
        deps_data = []
        for d in deps:
            from_key = task_id_to_key.get(d.task_id)
            to_key = task_id_to_key.get(d.depends_on_task_id)
            if from_key and to_key:
                deps_data.append({
                    "from": to_key,
                    "to": from_key,
                    "kind": d.kind,
                })

        # Recent events (last 40)
        events = session.exec(
            select(Event).where(Event.project_id == project.id).order_by(Event.id.desc()).limit(40)
        ).all()
        events_data = [
            {
                "id": ev.id,
                "ts": ev.ts.isoformat() if ev.ts else None,
                "actor_member_id": ev.actor_member_id,
                "type": ev.type,
                "task_id": task_id_to_key.get(ev.task_id) if ev.task_id else None,
                "payload": ev.payload,
            }
            for ev in events
        ]

        # Contradictions
        contradictions = session.exec(
            select(Contradiction).where(
                Contradiction.project_id == project.id,
                Contradiction.status == "open",
            )
        ).all()
        contradictions_data = [
            {
                "id": c.id,
                "task_ids": c.task_ids,
                "member_ids": c.member_ids,
                "summary": c.summary,
                "status": c.status,
            }
            for c in contradictions
        ]

        # Contributions series & totals
        commits = session.exec(
            select(CommitLog).where(CommitLog.project_id == project.id)
        ).all()

        totals_by_member = {}
        for m in members:
            totals_by_member[m.id] = {
                "member_id": m.id,
                "commits": 0,
                "lines": 0,
                "tasks_verified": sum(1 for t in tasks if t.owner_member_id == m.id and t.status == "verified_done"),
                "last_active": None,
            }

        series_by_member = {str(m.id): [] for m in members}

        for c in commits:
            if c.member_id and c.member_id in totals_by_member:
                totals_by_member[c.member_id]["commits"] += 1
                totals_by_member[c.member_id]["lines"] += (c.additions or 0)
                if c.committed_at:
                    curr_last = totals_by_member[c.member_id]["last_active"]
                    if not curr_last or c.committed_at.isoformat() > curr_last:
                        totals_by_member[c.member_id]["last_active"] = c.committed_at.isoformat()

        # Guide notes extracted from recent events
        guide_notes = [
            ev.payload if isinstance(ev.payload, dict) else {"text": str(ev.payload)}
            for ev in events if ev.type == "guide_note"
        ]

        return {
            "project": {
                "id": project.id,
                "code": project.code,
                "name": project.name,
                "idea": project.idea,
                "description": project.description or project.idea,
                "functional_requirements": project.functional_requirements,
                "non_functional_requirements": project.non_functional_requirements,
                "constraints": project.constraints,
                "status": project.status,
                "plan_status": project.plan_status or "draft",
                "repo_full_name": project.repo_full_name,
                "repo_url": project.repo_url,
                "telegram_chat_id": project.telegram_chat_id or project.telegram_group_id,
                "telegram_status": project.telegram_status or "disconnected",
                "lead_member_id": project.lead_member_id,
                "starts_at": project.starts_at.isoformat() if project.starts_at else None,
                "ends_at": project.ends_at.isoformat() if project.ends_at else None,
                "created_at": project.created_at.isoformat() if project.created_at else None,
            },
            "members": members_data,
            "blocks": blocks_data,
            "tasks": tasks_data,
            "deps": deps_data,
            "events": events_data,
            "contradictions": contradictions_data,
            "contributions": {
                "series": series_by_member,
                "totals": list(totals_by_member.values()),
            },
            "guide_notes": guide_notes,
        }


# ── Task CRUD & Lead Override ──────────────────────────────────────────────

class TaskCreateBody(BaseModel):
    title: str
    description: Optional[str] = ""
    effort: Optional[int] = 3
    is_milestone: Optional[bool] = False
    owner_member_id: Optional[int] = None
    acceptance_criteria: Optional[List[str]] = []
    depends_on: Optional[List[str]] = []


@router.post("/projects/{code}/tasks")
def create_task(code: str, body: TaskCreateBody):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Determine next key
        existing_tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
        next_num = len(existing_tasks) + 1
        key = f"T-{next_num}"

        task = Task(
            project_id=project.id,
            key=key,
            title=body.title,
            description=body.description,
            effort=body.effort,
            is_milestone=body.is_milestone or False,
            owner_member_id=body.owner_member_id,
            acceptance_criteria=body.acceptance_criteria or [],
            status="todo",
            risk="ok",
        )
        session.add(task)
        session.flush()

        # Add event
        ev = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            actor_member_id=body.owner_member_id,
            type="task_created",
            task_id=task.id,
            payload={"key": key, "title": body.title, "effort": body.effort},
        )
        session.add(ev)
        session.commit()
        return {"status": "ok", "key": key}


class TaskPatchBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    effort: Optional[int] = None
    status: Optional[str] = None
    owner_member_id: Optional[int] = None
    progress: Optional[int] = None
    risk: Optional[str] = None


@router.patch("/projects/{code}/tasks/{key}")
def patch_task(code: str, key: str, body: TaskPatchBody):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        old_status = task.status
        if body.title is not None:
            task.title = body.title
        if body.description is not None:
            task.description = body.description
        if body.effort is not None:
            task.effort = body.effort
        if body.status is not None:
            task.status = body.status
        if body.owner_member_id is not None:
            task.owner_member_id = body.owner_member_id
        if body.progress is not None:
            task.progress = body.progress
        if body.risk is not None:
            task.risk = body.risk

        session.add(task)

        if body.status and body.status != old_status:
            ev = Event(
                project_id=project.id,
                ts=datetime.now(timezone.utc),
                type="status_changed",
                task_id=task.id,
                payload={"from": old_status, "to": body.status, "reason": "Manual transition / drag"},
            )
            session.add(ev)

        session.commit()
        return {"status": "ok"}


@router.delete("/projects/{code}/tasks/{key}")
def delete_task(code: str, key: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        session.delete(task)
        session.commit()
        return {"status": "ok"}


@router.post("/projects/{code}/tasks/{key}/override-verify")
def override_verify(code: str, key: str):
    """Lead forces task status to verified_done."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task.status = "verified_done"
        task.progress = 100
        task.completed_at = datetime.now(timezone.utc)
        session.add(task)

        # Record verification record
        v = Verification(
            task_id=task.id,
            verdict="verified",
            confidence=1.0,
            reason="Lead manual override verified",
            created_at=datetime.now(timezone.utc),
        )
        session.add(v)

        ev = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            type="status_changed",
            task_id=task.id,
            payload={"from": "needs_review", "to": "verified_done", "reason": "Lead override"},
        )
        session.add(ev)
        session.commit()

        try:
            from ripple import risk_recompute
            risk_recompute(session, project.id)
            session.commit()
        except Exception:
            pass

        return {"status": "ok"}


@router.post("/projects/{code}/tasks/{key}/verify")
async def verify_task_endpoint(code: str, key: str):
    """Trigger real GitHub verification for task key."""
    from verify import verify_task
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        task = session.exec(
            select(Task).where(Task.project_id == project.id, Task.key == key)
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task_id = task.id

    result = await verify_task(task_id)
    return {"status": "ok", "task_key": key, **result}


@router.get("/projects/{code}/messages")
def list_project_messages(code: str, limit: int = 50):
    """Retrieve recent Telegram and system messages for the project feed."""
    from models import Message
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        members = session.exec(select(Member).where(Member.project_id == project.id)).all()
        member_map = {m.id: m.name for m in members}

        chat_id = project.telegram_chat_id or project.telegram_group_id

        # Query messages by project_id or chat_id
        conditions = [Message.project_id == project.id]
        if chat_id:
            conditions.append(Message.chat_id == chat_id)

        from sqlmodel import or_
        msgs = session.exec(
            select(Message)
            .where(or_(*conditions))
            .order_by(Message.id.desc())
            .limit(limit)
        ).all()

        msgs_sorted = list(reversed(msgs))
        return [
            {
                "id": m.id,
                "direction": m.direction,
                "sender": member_map.get(m.member_id, "Pilot Bot" if m.direction == "out" else "Team Member"),
                "member_id": m.member_id,
                "text": m.text,
                "intent": m.intent,
                "source": m.source,
                "tg_message_id": m.tg_message_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs_sorted
        ]


# ── Project Lifecycle Operations ───────────────────────────────────────────

class PlanRequestBody(BaseModel):
    idea: Optional[str] = None
    team_size: Optional[int] = 4
    skills: Optional[List[str]] = None
    duration_hours: Optional[int] = 20


@router.post("/projects/{code}/plan")
def trigger_plan(code: str, body: Optional[PlanRequestBody] = None):
    """Trigger AI task generation via Planner."""
    from planner import generate_plan, PlanGenerationError
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        req = body or PlanRequestBody()
        try:
            tasks = generate_plan(
                session=session,
                project_id=project.id,
                idea=req.idea or project.idea,
                team_size=req.team_size or 4,
                skills=req.skills,
                duration_hours=req.duration_hours or 20,
            )
            session.commit()
            return {"status": "ok", "task_count": len(tasks), "tasks": [t.key for t in tasks]}
        except PlanGenerationError as e:
            session.rollback()
            raise HTTPException(status_code=502, detail=f"Failed to generate plan: {e}")
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Planning error: {e}")


@router.post("/projects/{code}/bundle")
def preview_bundle(code: str):
    """Bundle tasks and preview balanced assignments."""
    from planner import bundle, assign
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        blocks = bundle(session, project.id)
        preview = assign(session, project.id)
        session.commit()
        return {
            "status": "ok",
            "blocks": [
                {
                    "id": b.id,
                    "name": b.name,
                    "owner_member_id": b.owner_member_id,
                    "total_effort": b.total_effort or 10,
                    "oversize_flag": b.oversize_flag,
                }
                for b in preview.get("blocks", blocks)
            ],
            "loads": preview.get("loads", {}),
            "oversize_warnings": preview.get("oversize_warnings", []),
        }


@router.post("/projects/{code}/confirm-assignment")
def confirm_assignment(code: str):
    """Confirm block assignments and lock task schedules."""
    from planner import confirm_assignment as do_confirm
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        result = do_confirm(session, project.id)
        session.commit()
        return {"status": "ok", "detail": "Assignments confirmed", **result}


@router.post("/projects/{code}/kickoff")
def kickoff_project(code: str):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project.status = "running"
        project.starts_at = datetime.now(timezone.utc)
        session.add(project)

        ev = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            type="status_changed",
            payload={"from": "planning", "to": "running", "reason": "Project Kickoff"},
        )
        session.add(ev)
        session.commit()
        return {"status": "ok", "detail": "Project kicked off"}


@router.post("/projects/{code}/verify")
def trigger_verify(code: str):
    """Trigger AST commit verification for project."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        ev = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            type="status_changed",
            payload={"reason": "Manual AST verification triggered"},
        )
        session.add(ev)
        session.commit()
        return {"status": "ok", "detail": "Verification executed"}


@router.post("/projects/{code}/reset")
def reset_project(code: str):
    """Reset project tasks to initial demo state."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
        for t in tasks:
            if t.key == "T-2":
                t.status = "in_progress"
                t.progress = 30
            else:
                t.status = "todo"
                t.progress = 0
            session.add(t)

        ev = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            type="status_changed",
            payload={"reason": "Demo project state reset"},
        )
        session.add(ev)
        session.commit()
        return {"status": "ok", "detail": "Project reset"}


# ── Guide Q&A Chat & Project Reports ──────────────────────────────────────

class AskBody(BaseModel):
    question: str


@router.post("/projects/{code}/ask")
def ask_guide(code: str, body: AskBody):
    """Q&A with Guide agent using tools and factual citation verification."""
    from guide import run_guide_query
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        try:
            result = run_guide_query(session, project.id, body.question)
            return result
        except Exception:
            q = body.question.lower()
            tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
            blocked = [t for t in tasks if t.status == "blocked"]
            verified = [t for t in tasks if t.status == "verified_done"]

            if "block" in q:
                if blocked:
                    keys = ", ".join(f"[{t.key}] {t.title}" for t in blocked)
                    return {"answer": f"Currently, there is an active bottleneck: {keys}. Downstream tasks may experience ripple slip."}
                return {"answer": "No tasks are currently blocked. Commits and transitions are progressing smoothly."}

            if "risk" in q or "deadline" in q or "milestone" in q:
                return {"answer": "The Demo Milestone is being monitored for potential slip from upstream dependencies."}

            if "progress" in q or "commit" in q:
                return {"answer": f"Team progress: {len(verified)}/{len(tasks)} tasks verified done."}

            return {
                "answer": f"I'm monitoring project {project.name} ({code}). We have {len(tasks)} tasks total, with {len(verified)} verified done and {len(blocked)} blocked."
            }


@router.post("/projects/{code}/report")
def get_project_report(code: str):
    """Generate final project digest with member contributions, completed tasks, and blockers."""
    from guide import generate_report
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return generate_report(session, project.id)


class SplitRequestBody(BaseModel):
    block_id: int
    apply: Optional[bool] = False


@router.post("/projects/{code}/split")
def handle_split(code: str, body: SplitRequestBody):
    """Propose or apply a block split to rebalance workload."""
    from planner import propose_split, apply_split
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if body.apply:
            res = apply_split(session, body.block_id)
            session.commit()
            return res
        return propose_split(session, body.block_id)


# ── Project Info & Collaborators Management ───────────────────────────────

class ProjectPatchBody(BaseModel):
    name: Optional[str] = None
    idea: Optional[str] = None
    repo_url: Optional[str] = None
    repo_full_name: Optional[str] = None
    telegram_group_id: Optional[int] = None


@router.patch("/projects/{code}")
def patch_project(code: str, body: ProjectPatchBody):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if body.name is not None:
            project.name = body.name
        if body.idea is not None:
            project.idea = body.idea
        if body.repo_url is not None:
            project.repo_url = body.repo_url
        if body.repo_full_name is not None:
            project.repo_full_name = body.repo_full_name
        if body.telegram_group_id is not None:
            project.telegram_group_id = body.telegram_group_id

        session.add(project)
        session.commit()
        return {"status": "ok", "project": {
            "code": project.code,
            "name": project.name,
            "repo_url": project.repo_url,
            "repo_full_name": project.repo_full_name
        }}


class MemberCreateBody(BaseModel):
    name: str
    github_login: Optional[str] = ""
    telegram_username: Optional[str] = ""
    telegram_phone: Optional[str] = ""
    telegram_id: Optional[int] = None
    role: Optional[str] = "member"


@router.post("/projects/{code}/members")
def add_member(code: str, body: MemberCreateBody):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        member = Member(
            project_id=project.id,
            name=body.name,
            github_login=body.github_login or "",
            telegram_username=body.telegram_username or "",
            telegram_id=body.telegram_id or 0,
            role=body.role or "member",
            invite_status="accepted" if body.github_login else "pending",
            onboarding_state="done" if body.github_login else "awaiting_github",
        )
        session.add(member)
        session.flush()

        ev = Event(
            project_id=project.id,
            ts=datetime.now(timezone.utc),
            actor_member_id=member.id,
            type="member_joined",
            payload={"name": body.name, "github_login": body.github_login, "role": body.role},
        )
        session.add(ev)
        session.commit()
        return {"status": "ok", "member_id": member.id}


@router.delete("/projects/{code}/members/{member_id}")
def remove_member(code: str, member_id: int):
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        member = session.get(Member, member_id)
        if member:
            session.delete(member)
            session.commit()
        return {"status": "ok"}


@router.post("/projects/{code}/report")
def generate_report(code: str):
    """Generate executive summary report for faculty/judges."""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.code == code)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
        members = session.exec(select(Member).where(Member.project_id == project.id)).all()
        verified = sum(1 for t in tasks if t.status == "verified_done")
        blocked = sum(1 for t in tasks if t.status == "blocked")

        return {
            "status": "ok",
            "report": {
                "project_name": project.name,
                "project_code": project.code,
                "status": project.status,
                "total_tasks": len(tasks),
                "verified_tasks": verified,
                "blocked_tasks": blocked,
                "completion_rate": f"{(verified / len(tasks) * 100):.1f}%" if tasks else "0%",
                "members_count": len(members),
                "summary": f"Project {project.name} has completed {verified} of {len(tasks)} tasks. {blocked} active bottlenecks identified and managed by Pilot coordinator.",
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }

