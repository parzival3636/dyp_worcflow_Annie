"""
MemberRepository interface and stub for Pilot project members.
"""
from __future__ import annotations

from typing import List, Optional, Protocol
from pydantic import BaseModel


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
