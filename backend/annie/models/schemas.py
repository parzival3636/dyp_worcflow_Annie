from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── Repo / Collaborator Models ──────────────────────────────

class CreateRepoRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    private: bool = True
    collaborators: list[str] = []


class CollaboratorStatus(BaseModel):
    username: str
    status: str  # "invited" | "accepted" | "failed"
    invited_at: Optional[datetime] = None


class RepoResponse(BaseModel):
    repo_name: str
    repo_url: str
    full_name: Optional[str] = None
    collaborators: list[CollaboratorStatus]


# ─── Task Models ──────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: str
    keywords: list[str]
    repo_name: str
    assigned_to: Optional[list[str]] = []


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    keywords: list[str]
    repo_name: str
    assigned_to: list[str]
    status: str  # "pending" | "in_progress" | "complete"
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# ─── Verification / Commit Models ─────────────────────────────

class VerificationResult(BaseModel):
    task_id: str
    commit_sha: str
    confidence_score: float
    reasoning: str
    status_updated_to: Optional[str] = None
    processed_at: datetime


class WebhookEvent(BaseModel):
    id: str
    repo_name: str
    commit_sha: str
    commit_message: str
    author: str
    diff_url: str
    raw_payload: dict
    status: str  # "pending" | "processing" | "processed" | "failed"
    created_at: datetime
