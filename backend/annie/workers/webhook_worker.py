import asyncio
import logging
from datetime import datetime, timezone

from annie.core.database import get_supabase
from annie.core.config import get_settings
from annie.services.github_service import GitHubService
from annie.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class WebhookWorker:
    """
    Background worker that polls Supabase for pending webhook events,
    fetches commit diffs, runs Gemini verification, and updates task statuses.
    """

    def __init__(self):
        self.settings = get_settings()
        self._db = None
        self._github = None
        self._gemini = None
        self.running = False
        self.poll_interval = 5  # seconds

    @property
    def db(self):
        if self._db is None:
            self._db = get_supabase()
        return self._db

    @property
    def github(self):
        if self._github is None:
            self._github = GitHubService()
        return self._github

    @property
    def gemini(self):
        if self._gemini is None:
            self._gemini = GeminiService()
        return self._gemini

    async def start(self):
        self.running = True
        logger.info("Annie Webhook worker started — polling Supabase every %ds", self.poll_interval)
        while self.running:
            try:
                await self._process_pending_events()
            except Exception as e:
                logger.error("Annie Worker loop error: %s", e)
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self.running = False
        logger.info("Annie Webhook worker stopped")

    async def _process_pending_events(self):
        try:
            # Fetch all pending events
            result = (
                self.db.table("webhook_events")
                .select("*")
                .eq("status", "pending")
                .limit(10)
                .execute()
            )
            events = result.data or []

            for event in events:
                await self._handle_event(event)
        except Exception as e:
            logger.debug("Failed checking pending webhook events: %s", e)

    async def _handle_event(self, event: dict):
        event_id = event["id"]
        repo_name = event["repo_name"]
        commit_sha = event["commit_sha"]

        logger.info("Processing event %s — commit %s on %s", event_id, commit_sha, repo_name)

        # Mark as processing
        self.db.table("webhook_events").update({"status": "processing"}).eq("id", event_id).execute()

        try:
            # 1. Fetch the diff from GitHub
            owner = self.settings.github_username
            full_repo_path = f"{owner}/{repo_name}" if "/" not in repo_name else repo_name
            diff = await self.github.fetch_commit_diff(full_repo_path, commit_sha)

            # 2. Find tasks associated with this repo (flexible matching for spaces/hyphens/owner prefix)
            tasks_result = (
                self.db.table("tasks")
                .select("*")
                .neq("status", "complete")
                .execute()
            )
            all_active_tasks = tasks_result.data or []

            def normalize_name(s: str) -> str:
                return (s or "").lower().replace("-", "").replace("_", "").replace(" ", "").split("/")[-1]

            target_norm = normalize_name(repo_name)
            tasks = [
                t for t in all_active_tasks
                if normalize_name(t.get("repo_name", "")) == target_norm
            ]

            if not tasks:
                logger.info("No active tasks matching repo %s (searched %d tasks)", repo_name, len(all_active_tasks))
                self._mark_event(event_id, "processed")
                return

            # 3. Verify each task against the commit
            for task in tasks:
                result = await self.gemini.verify_commit(
                    task_title=task["title"],
                    task_description=task["description"],
                    task_keywords=task.get("keywords", []),
                    commit_sha=commit_sha,
                    commit_message=event.get("commit_message", ""),
                    author=event.get("author", ""),
                    diff=diff,
                )

                confidence = result.get("confidence_score", 0)
                new_status = None

                # 4. Auto-update task status if confidence >= threshold
                if confidence >= self.settings.completion_threshold:
                    new_status = "complete"
                    self.db.table("tasks").update(
                        {
                            "status": "complete",
                            "confidence_score": confidence,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", task["id"]).execute()
                    logger.info("Task %s marked COMPLETE (score: %s)", task["id"], confidence)
                elif confidence >= 50:
                    new_status = "in_progress"
                    self.db.table("tasks").update(
                        {
                            "status": "in_progress",
                            "confidence_score": confidence,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", task["id"]).execute()

                # 5. Store verification record
                self.db.table("verifications").insert(
                    {
                        "task_id": task["id"],
                        "event_id": event_id,
                        "commit_sha": commit_sha,
                        "confidence_score": confidence,
                        "reasoning": result.get("reasoning", ""),
                        "matched_keywords": result.get("matched_keywords", []),
                        "status_updated_to": new_status,
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).execute()

                # 6. Post native GitHub Commit Status (visible on GitHub commits/PRs)
                try:
                    if confidence >= self.settings.completion_threshold:
                        state = "success"
                        desc = f"Annie: Verified ({confidence}% confidence)"
                    elif confidence >= 50:
                        state = "pending"
                        desc = f"Annie: In progress ({confidence}% confidence)"
                    else:
                        state = "failure"
                        desc = f"Annie: Unverified ({confidence}% confidence)"

                    self.github.create_commit_status(
                        repo_full_name=full_repo_path,
                        commit_sha=commit_sha,
                        state=state,
                        description=desc,
                        context=f"annie/{task['id'][:8]}",
                    )
                except Exception as status_err:
                    logger.warning("Could not set commit status for %s: %s", commit_sha, status_err)

            self._mark_event(event_id, "processed")

        except Exception as e:
            logger.error("Failed to process event %s: %s", event_id, e)
            self._mark_event(event_id, "failed")

    def _mark_event(self, event_id: str, status: str):
        self.db.table("webhook_events").update({"status": status}).eq("id", event_id).execute()
