from fastapi import APIRouter, HTTPException
from app.models.schemas import CreateRepoRequest, RepoResponse
from app.services.github_service import GitHubService
from app.core.config import get_settings
from app.core.database import get_supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repos", tags=["Repositories"])


@router.post("/create", response_model=RepoResponse)
async def create_repo(payload: CreateRepoRequest):
    """
    Create a GitHub repository, invite collaborators, register webhook,
    and persist the repo record to Supabase.
    """
    settings = get_settings()
    gh = GitHubService()
    db = get_supabase()

    # 1. Create the repo on GitHub
    try:
        repo_info = gh.create_repo(
            name=payload.name,
            description=payload.description,
            private=payload.private,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create repo: {str(e)}")

    full_name = repo_info["full_name"]

    # 2. Invite collaborators
    collab_statuses = []
    for username in payload.collaborators:
        status = gh.invite_collaborator(full_name, username)
        collab_statuses.append(status)

    # 3. Register the Supabase edge function as a webhook
    webhook_url = f"{settings.supabase_url}/functions/v1/github-webhook"
    gh.setup_webhook(full_name, webhook_url)

    # 4. Automatically set up GitHub Actions verification workflow in the repo
    gh.setup_workflow_file(full_name)

    # 5. Persist repo to Supabase (upsert to handle re-registration)
    db.table("repos").upsert(
        {
            "name": payload.name,
            "full_name": full_name,
            "url": repo_info["repo_url"],
            "owner": settings.github_username,
            "collaborators": [c.username for c in collab_statuses],
        },
        on_conflict="full_name",
    ).execute()

    logger.info("Repo %s created and stored", full_name)

    return RepoResponse(
        repo_name=repo_info["repo_name"],
        repo_url=repo_info["repo_url"],
        collaborators=collab_statuses,
    )


@router.get("/{repo_name}/collaborators")
async def get_collaborators(repo_name: str):
    """Get current collaborator invitation statuses for a repo."""
    settings = get_settings()
    gh = GitHubService()
    full_name = f"{settings.github_username}/{repo_name}"
    statuses = gh.get_collaborator_statuses(full_name)
    return {"repo": repo_name, "collaborators": statuses}


@router.get("/")
async def list_repos():
    """List all repos tracked in Supabase."""
    db = get_supabase()
    result = db.table("repos").select("*").order("created_at", desc=True).execute()
    return {"repos": result.data}
