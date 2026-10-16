"""
Pilot – Authentication & Authorization module.
Handles user registration, login, JWT token issuance & verification,
HttpOnly cookie sessions, and role-based access control.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

import bcrypt
import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlmodel import select

from config import get_settings
from db import get_session
from models import User

COOKIE_NAME = "pilot_session"


# ── Pydantic Request / Response schemas ──────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "leader"  # leader | guide | member


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: Optional[datetime] = None


# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ── Token creation & decoding ────────────────────────────────────────────────

def create_access_token(user_id: int, email: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.PyJWTError:
        return None


def set_auth_cookie(response: Response, token: str):
    settings = get_settings()
    # 7 days max age
    max_age = settings.jwt_expire_minutes * 60
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        samesite="lax",
        secure=False,  # set True in HTTPS production
        path="/",
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )


# ── Dependency: Get current user ─────────────────────────────────────────────

def get_token_from_request(
    request: Request,
    pilot_session: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    # 1. Cookie
    if pilot_session:
        return pilot_session
    # 2. Authorization header: Bearer <token>
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
) -> Optional[User]:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None

    with get_session() as session:
        user = session.get(User, user_id)
        return user


def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_role(*allowed_roles: str) -> Callable:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker
