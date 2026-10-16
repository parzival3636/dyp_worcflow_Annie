"""
MemberRepository interface and implementations for Pilot project members.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Protocol
from pydantic import BaseModel

logger = logging.getLogger("transcribe.members_repo")


class ProjectMember(BaseModel):
    member_id: str
    full_name: str
    aliases: List[str] = []
    telegram_id: Optional[str] = None


class MemberRepository(Protocol):
    def get_project_members(self, project_id: str) -> List[ProjectMember]:
        ...


class InMemoryMemberRepository:
    def __init__(self, members_by_project: dict[str, list[ProjectMember]] | None = None):
        self.members_by_project = members_by_project or {}

    def get_project_members(self, project_id: str) -> List[ProjectMember]:
        return self.members_by_project.get(project_id, [])


class PilotDbMemberRepository:
    """Fetches real team members from Pilot database."""

    def get_project_members(self, project_id: str) -> List[ProjectMember]:
        try:
            from db import get_session
            from models import Project, Member
            from sqlmodel import select
        except ImportError:
            from backend.db import get_session
            from backend.models import Project, Member
            from sqlmodel import select

        with get_session() as session:
            project = None
            if str(project_id).isdigit():
                project = session.get(Project, int(project_id))
            if not project:
                project = session.exec(
                    select(Project).where(Project.code == project_id)
                ).first()

            if not project:
                return []

            members = session.exec(
                select(Member).where(Member.project_id == project.id)
            ).all()

            results = []
            for m in members:
                aliases = list(m.aliases or [])
                if m.name and m.name not in aliases:
                    aliases.append(m.name)
                if m.github_login and m.github_login not in aliases:
                    aliases.append(m.github_login)

                results.append(
                    ProjectMember(
                        member_id=str(m.id),
                        full_name=m.name or "Member",
                        aliases=aliases,
                        telegram_id=str(m.telegram_id) if m.telegram_id else None,
                    )
                )
            return results
