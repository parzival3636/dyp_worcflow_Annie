"""
Pilot – Authentication REST endpoints.
/api/auth/signup, /api/auth/login, /api/auth/logout, /api/auth/me, /api/auth/projects
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import select

from auth import (
    LoginRequest,
    SignupRequest,
    UserResponse,
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from db import get_session
from models import Member, Project, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse)
def signup(payload: SignupRequest, response: Response):
    """Register a new user account (defaults to Leader)."""
    with get_session() as session:
        # Check existing user
        existing = session.exec(select(User).where(User.email == payload.email.lower())).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists",
            )

        # Enforce minimum password length
        if len(payload.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long",
            )

        user = User(
            email=payload.email.lower(),
            name=payload.name.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role if payload.role in ("leader", "guide", "member") else "leader",
        )
        session.add(user)
        session.flush()
        session.refresh(user)

        # Create JWT token and set HttpOnly cookie
        token = create_access_token(user.id, user.email, user.role)
        set_auth_cookie(response, token)

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            created_at=user.created_at,
        )


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response):
    """Authenticate with email and password, setting an HttpOnly cookie."""
    with get_session() as session:
        user = session.exec(select(User).where(User.email == payload.email.lower())).first()
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = create_access_token(user.id, user.email, user.role)
        set_auth_cookie(response, token)

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            created_at=user.created_at,
        )


@router.post("/logout")
def logout(response: Response):
    """Log out by clearing the session cookie."""
    clear_auth_cookie(response)
    return {"ok": True, "message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        created_at=current_user.created_at,
    )


@router.get("/projects")
def get_user_projects(current_user: User = Depends(get_current_user)):
    """List all projects where current user is leader or participating member."""
    with get_session() as session:
        # 1. Projects where user is leader
        leader_projects = session.exec(
            select(Project).where(Project.leader_user_id == current_user.id)
        ).all()

        # 2. Projects where user is member by user_id or email
        member_records = session.exec(
            select(Member).where(
                (Member.user_id == current_user.id) | (Member.email == current_user.email)
            )
        ).all()
        member_proj_ids = {m.project_id for m in member_records if m.project_id}

        other_projects = []
        if member_proj_ids:
            other_projects = session.exec(
                select(Project).where(Project.id.in_(list(member_proj_ids)))
            ).all()

        # Deduplicate by id
        all_projs = {p.id: p for p in (leader_projects + other_projects)}

        # If user has no projects yet and demo projects exist, include them for convenience
        if not all_projs:
            demo_projs = session.exec(select(Project).limit(5)).all()
            for p in demo_projs:
                all_projs[p.id] = p

        return [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "description": p.description or p.idea,
                "status": p.status,
                "repo_full_name": p.repo_full_name,
                "repo_url": p.repo_url,
                "telegram_chat_id": p.telegram_chat_id or p.telegram_group_id,
                "telegram_status": p.telegram_status or "disconnected",
                "is_leader": p.leader_user_id == current_user.id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in all_projs.values()
        ]
