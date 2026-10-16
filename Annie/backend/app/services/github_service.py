import httpx
from github import Github, GithubException
from app.core.config import get_settings
from app.models.schemas import CollaboratorStatus
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

DEFAULT_WORKFLOW_CONTENT = """name: Annie Task Verification

on:
  push:
    branches: [ "**" ]
  pull_request:
    branches: [ "**" ]
  workflow_dispatch:

jobs:
  verify:
    name: Annie AI Code & Task Verification
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository code
        uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - name: Inspect Commit & Changes
        run: |
          echo "=========================================="
          echo "Annie Task Verification Pipeline"
          echo "=========================================="
          echo "Commit: ${{ github.sha }}"
          echo "Author: ${{ github.actor }}"
          echo "Ref:    ${{ github.ref }}"
          echo "=========================================="
          git diff-tree --no-commit-id --name-only -r ${{ github.sha }} || true
          echo "=========================================="
          echo "Verified by Annie Engine via Real-time Webhook and Gemini AI."

      - name: Status Summary
        run: |
          echo "Annie verification active. Live results streaming to Annie Dashboard."
"""


class GitHubService:
    def __init__(self):
        self.settings = get_settings()
        self.gh = Github(self.settings.github_token)
        self.headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def create_repo(self, name: str, description: str = "", private: bool = True) -> dict:
        """Create a new GitHub repository for the authenticated user."""
        user = self.gh.get_user()
        repo = user.create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=True,
        )
        logger.info(f"Created repo: {repo.full_name}")
        return {
            "repo_name": repo.name,
            "repo_url": repo.html_url,
            "full_name": repo.full_name,
        }

    def invite_collaborator(self, repo_full_name: str, username: str) -> CollaboratorStatus:
        """Invite a GitHub user as a collaborator to the given repo."""
        try:
            repo = self.gh.get_repo(repo_full_name)
            repo.add_to_collaborators(username, permission="push")
            logger.info(f"Invited {username} to {repo_full_name}")
            return CollaboratorStatus(
                username=username,
                status="invited",
                invited_at=datetime.now(timezone.utc),
            )
        except GithubException as e:
            logger.error(f"Failed to invite {username}: {e}")
            return CollaboratorStatus(username=username, status="failed")

    def setup_webhook(self, repo_full_name: str, webhook_url: str) -> bool:
        """Register a webhook on the repo pointing to the Supabase edge function."""
        try:
            repo = self.gh.get_repo(repo_full_name)
            config = {
                "url": webhook_url,
                "content_type": "json",
                "secret": self.settings.github_webhook_secret,
            }
            repo.create_hook(
                name="web",
                config=config,
                events=["push"],
                active=True,
            )
            logger.info(f"Webhook registered on {repo_full_name} → {webhook_url}")
            return True
        except GithubException as e:
            logger.error(f"Failed to register webhook: {e}")
            return False

    async def fetch_commit_diff(self, repo_full_name: str, commit_sha: str) -> str:
        """Fetch the full unified diff for a given commit SHA."""
        url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={**self.headers, "Accept": "application/vnd.github.diff"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.text

    def get_collaborator_statuses(self, repo_full_name: str) -> list[dict]:
        """Fetch pending invitations and accepted collaborators for a repo."""
        statuses = []
        try:
            repo = self.gh.get_repo(repo_full_name)
            # Pending invitations
            for inv in repo.get_pending_invitations():
                statuses.append({
                    "username": inv.invitee.login,
                    "status": "invited",
                    "invited_at": inv.created_at.isoformat(),
                })
            # Accepted collaborators (excluding owner)
            owner = self.gh.get_user().login
            for collab in repo.get_collaborators():
                if collab.login != owner:
                    statuses.append({
                        "username": collab.login,
                        "status": "accepted",
                        "invited_at": None,
                    })
        except GithubException as e:
            logger.error(f"Failed to fetch collaborator statuses: {e}")
        return statuses

    def setup_workflow_file(self, repo_full_name: str) -> bool:
        """Commit .github/workflows/verify.yml to repo if not already present."""
        try:
            repo = self.gh.get_repo(repo_full_name)
            try:
                repo.get_contents(".github/workflows/verify.yml")
                logger.info(f"Workflow file already exists in {repo_full_name}")
                return True
            except GithubException as e:
                if e.status != 404:
                    raise e

            branch = repo.default_branch or "main"
            repo.create_file(
                path=".github/workflows/verify.yml",
                message="ci: add Annie task verification workflow",
                content=DEFAULT_WORKFLOW_CONTENT,
                branch=branch,
            )
            logger.info(f"Created .github/workflows/verify.yml in {repo_full_name} on branch {branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup workflow file in {repo_full_name}: {e}")
            return False

    def create_commit_status(
        self,
        repo_full_name: str,
        commit_sha: str,
        state: str,
        description: str,
        context: str = "annie/ai-verification",
    ) -> bool:
        """Create a GitHub commit status check (success, pending, failure)."""
        try:
            repo = self.gh.get_repo(repo_full_name)
            commit = repo.get_commit(commit_sha)
            commit.create_status(
                state=state,
                description=description[:140],
                context=context,
            )
            logger.info(f"Created commit status '{state}' on {repo_full_name}@{commit_sha[:8]}")
            return True
        except Exception as e:
            logger.error(f"Failed to create commit status on {repo_full_name}@{commit_sha}: {e}")
            return False
