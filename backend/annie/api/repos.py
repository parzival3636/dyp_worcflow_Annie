from fastapi import APIRouter, HTTPException, Request, Header
from annie.models.schemas import CreateRepoRequest, RepoResponse
from annie.services.github_service import GitHubService
from annie.core.config import get_settings
from annie.core.database import get_supabase
import hmac
import hashlib
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repos", tags=["Annie Repositories"])


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
            description=payload.description or "",
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

    # 3. Register the Supabase edge function (or local API webhook if configured)
    webhook_url = f"{settings.supabase_url}/functions/v1/github-webhook"
    gh.setup_webhook(full_name, webhook_url)

    # 4. Automatically set up GitHub Actions verification workflow in the repo
    gh.setup_workflow_file(full_name)

    # 5. Persist repo to Supabase (upsert to handle re-registration)
    try:
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
        logger.info("Repo %s created and stored in Supabase", full_name)
    except Exception as db_err:
        logger.warning("Could not persist repo to Supabase table 'repos': %s", db_err)

    return RepoResponse(
        repo_name=repo_info["repo_name"],
        repo_url=repo_info["repo_url"],
        full_name=full_name,
        collaborators=collab_statuses,
    )


@router.get("/{repo_name}/collaborators")
async def get_collaborators(repo_name: str):
    """Get current collaborator invitation statuses for a repo."""
    settings = get_settings()
    gh = GitHubService()
    full_name = f"{settings.github_username}/{repo_name}" if "/" not in repo_name else repo_name
    statuses = gh.get_collaborator_statuses(full_name)
    return {"repo": repo_name, "collaborators": statuses}


@router.get("/")
async def list_repos():
    """List all repos tracked in Supabase."""
    db = get_supabase()
    try:
        result = db.table("repos").select("*").order("created_at", desc=True).execute()
        return {"repos": result.data or []}
    except Exception as e:
        logger.warning("Failed listing repos from Supabase: %s", e)
        return {"repos": []}


@router.post("/webhook")
async def handle_direct_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
):
    """
    Direct GitHub webhook receiver (alternative or complement to Supabase Edge Function).
    Validates HMAC-SHA256 signature and enqueues push commits into webhook_events.
    """
    settings = get_settings()
    body_bytes = await request.body()

    # Signature verification if secret configured
    if settings.github_webhook_secret and x_hub_signature_256:
        mac = hmac.new(settings.github_webhook_secret.encode(), body_bytes, hashlib.sha256)
        expected = "sha256=" + mac.hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if x_github_event != "push":
        return {"message": f"Ignored event: {x_github_event}"}

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}")

    commits = payload.get("commits") or []
    if not commits:
        return {"message": "No commits in push payload"}

    db = get_supabase()
    events = [
        {
            "repo_name": payload.get("repository", {}).get("name"),
            "commit_sha": commit.get("id"),
            "commit_message": commit.get("message"),
            "author": commit.get("author", {}).get("username") or commit.get("author", {}).get("name") or "unknown",
            "diff_url": commit.get("url"),
            "raw_payload": payload,
            "status": "pending",
        }
        for commit in commits
    ]

    res = db.table("webhook_events").insert(events).execute()
    logger.info("Enqueued %d push events from direct webhook", len(events))
    return {"received": len(events), "status": "queued"}
