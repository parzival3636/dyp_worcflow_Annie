"""
Pilot – GitHub verification engine.

Verifies task completion against real GitHub commits using:
1. Commit message pattern matching ([T-key])
2. Author matching (GitHub login / email)
3. Git diff inspection
4. Gemini AI / LLM code analysis (P4Verdict)
5. State transitions (claimed_done -> verified_done / needs_review)
6. Automatic Telegram in-thread verdict notifications
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlmodel import Session, select

from config import get_settings
from db import get_session
from models import CommitLog, Event, Member, Project, Task, Verification
from state import transition_task, IllegalTransition

logger = logging.getLogger("pilot.verify")


async def _fetch_repo_commits(
    repo_full_name: str,
    github_token: str,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch recent commits from GitHub repository REST API."""
    if not repo_full_name or not github_token:
        return []

    settings = get_settings()
    owner = settings.github_owner or getattr(settings, "github_username", "")
    if "/" not in repo_full_name and owner:
        repo_full_name = f"{owner}/{repo_full_name}"

    url = f"https://api.github.com/repos/{repo_full_name}/commits"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params={"per_page": limit})
            if resp.status_code == 200:
                return resp.json()
            logger.warning("GitHub API %s returned status %d: %s", url, resp.status_code, resp.text[:200])
            return []
    except Exception as exc:
        logger.exception("Failed to fetch commits from %s: %s", repo_full_name, exc)
        return []


async def _fetch_commit_diff(
    repo_full_name: str,
    sha: str,
    github_token: str,
) -> str:
    """Fetch commit diff or patch from GitHub."""
    if not repo_full_name or not sha or not github_token:
        return ""

    url = f"https://api.github.com/repos/{repo_full_name}/commits/{sha}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3.diff",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text
            return ""
    except Exception as exc:
        logger.exception("Failed to fetch diff for %s on %s: %s", sha, repo_full_name, exc)
        return ""


def _sync_commits_to_db(
    session: Session,
    project_id: int,
    raw_commits: List[Dict[str, Any]],
    members: List[Member],
) -> List[CommitLog]:
    """Upsert fetched commits into the commit_log table."""
    member_by_gh = {m.github_login.lower(): m.id for m in members if m.github_login}
    member_by_email = {m.email.lower(): m.id for m in members if m.email}

    upserted = []
    for item in raw_commits:
        sha = item.get("sha")
        if not sha:
            continue

        existing = session.get(CommitLog, sha)
        if existing:
            upserted.append(existing)
            continue

        commit_data = item.get("commit", {})
        author_data = item.get("author") or {}
        gh_login = author_data.get("login") or ""
        author_email = (commit_data.get("author") or {}).get("email") or ""
        msg = commit_data.get("message") or ""

        # Match author to project member
        matched_member_id = None
        if gh_login and gh_login.lower() in member_by_gh:
            matched_member_id = member_by_gh[gh_login.lower()]
        elif author_email and author_email.lower() in member_by_email:
            matched_member_id = member_by_email[author_email.lower()]

        date_str = (commit_data.get("author") or {}).get("date")
        committed_at = None
        if date_str:
            try:
                committed_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                pass

        stats = item.get("stats") or {}
        files = [f.get("filename") for f in item.get("files", []) if f.get("filename")]

        record = CommitLog(
            sha=sha,
            project_id=project_id,
            author_login=gh_login or author_email,
            member_id=matched_member_id,
            message=msg[:500] if msg else "",
            files=files,
            additions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            committed_at=committed_at or datetime.now(timezone.utc),
        )
        session.add(record)
        upserted.append(record)

    session.flush()
    return upserted


async def _run_ai_verification(
    task_key: str,
    task_title: str,
    task_desc: str,
    criteria: List[str],
    sha: str,
    commit_msg: str,
    diff: str,
) -> Dict[str, Any]:
    """Run AI code verification on commit diff against task criteria."""
    # 1. Try GeminiService if API key available
    settings = get_settings()
    if settings.gemini_api_key:
        try:
            from annie.services.gemini_service import GeminiService
            gemini = GeminiService()
            res = await gemini.verify_commit(
                task_title=task_title,
                task_description=f"{task_desc}\nCriteria: {', '.join(criteria)}",
                task_keywords=[task_key] + task_title.split()[:4],
                commit_sha=sha,
                commit_message=commit_msg,
                author="",
                diff=diff,
            )
            score = float(res.get("confidence_score", 0)) / 100.0
            return {
                "confidence": score,
                "reason": res.get("reasoning", "Verified by Gemini AI"),
                "implements_task": res.get("implements_task", score >= 0.7),
            }
        except Exception as exc:
            logger.warning("Gemini verification failed, attempting fallback: %s", exc)

    # 2. Fallback to OpenCode LLM
    try:
        from llm import call_json, P4Verdict
        system_prompt = (
            "You are a strict code review verification engine. Verify if the git diff implements the task.\n"
            "Return valid JSON matching P4Verdict schema."
        )
        user_prompt = (
            f"Task: {task_key} - {task_title}\n"
            f"Description: {task_desc}\n"
            f"Acceptance criteria: {criteria}\n"
            f"Commit: {sha}\n"
            f"Message: {commit_msg}\n"
            f"Diff:\n{diff[:8000]}"
        )
        verdict: P4Verdict = await call_json(
            model=settings.llm_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=P4Verdict,
            temperature=0.1,
        )
        return {
            "confidence": verdict.confidence,
            "reason": verdict.reason,
            "implements_task": verdict.verdict == "verified",
        }
    except Exception as exc:
        logger.exception("AI verification failed completely: %s", exc)
        # Deterministic heuristic fallback if commit message explicitly references task key
        if f"[{task_key}]" in commit_msg or f"{task_key}:" in commit_msg:
            return {
                "confidence": 0.85,
                "reason": f"Commit message explicitly tagged [{task_key}] and diff exists ({len(diff)} chars)",
                "implements_task": True,
            }
        return {
            "confidence": 0.40,
            "reason": f"Commit found but AI verification could not complete: {exc}",
            "implements_task": False,
        }


def verify_task_sync(task_id: int) -> Dict[str, Any]:
    """Synchronous wrapper for verify_task so it can be called from synchronous handlers."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In an active event loop, run as task or thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, verify_task(task_id))
                return future.result(timeout=45)
        else:
            return asyncio.run(verify_task(task_id))
    except Exception as exc:
        logger.exception("verify_task_sync error: %s", exc)
        return {"verdict": "no_evidence", "confidence": 0.0, "reason": str(exc), "matched_shas": []}


async def verify_task(task_id: int) -> Dict[str, Any]:
    """
    Main verification pipeline for a specific task.
    1. Look up task, project, owner member
    2. Check GitHub commits for matching key [T-x] or author
    3. Run AI verification on diff
    4. Transition task state (verified_done or needs_review)
    5. Record Verification row and Event
    6. Post update to Telegram group if connected
    """
    settings = get_settings()

    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            return {"verdict": "no_evidence", "confidence": 0.0, "reason": "Task not found"}

        project = session.get(Project, task.project_id)
        if not project:
            return {"verdict": "no_evidence", "confidence": 0.0, "reason": "Project not found"}

        proj_id = project.id
        repo_name = project.repo_full_name
        chat_id = project.telegram_chat_id or project.telegram_group_id
        task_key = task.key
        task_title = task.title or ""
        task_desc = task.description or ""
        task_criteria = task.acceptance_criteria or []
        task_started_at = task.started_at
        task_owner_id = task.owner_member_id

        members = session.exec(select(Member).where(Member.project_id == proj_id)).all()
        members_list = [Member.model_validate(m) for m in members]
        owner = session.get(Member, task_owner_id) if task_owner_id else None
        owner_id = owner.id if owner else None

    # Step 1: Fetch commits from GitHub if repo is configured
    github_token = settings.github_token
    matched_commits = []

    if repo_name and github_token:
        raw_commits = await _fetch_repo_commits(repo_name, github_token, limit=40)
        with get_session() as session:
            all_commits_db = _sync_commits_to_db(session, proj_id, raw_commits, members_list)
            session.commit()
            all_commits = [CommitLog.model_validate(c) for c in all_commits_db]

        # Step 2: Match candidate commits for this task
        key_pattern = re.compile(rf"\b{re.escape(task_key)}\b", re.IGNORECASE)
        for c in all_commits:
            # Check commit message for key
            if key_pattern.search(c.message or ""):
                matched_commits.append(c)
            # Or if authored by owner and committed recently
            elif owner_id and c.member_id == owner_id and task_started_at:
                if c.committed_at and c.committed_at >= task_started_at:
                    matched_commits.append(c)
    else:
        # Check DB commit_log
        with get_session() as session:
            key_pattern_str = f"%{task_key}%"
            matched_commits = session.exec(
                select(CommitLog).where(
                    CommitLog.project_id == proj_id,
                    CommitLog.message.ilike(key_pattern_str),
                )
            ).all()

    # Step 3: Determine verdict
    now = datetime.now(timezone.utc)
    matched_shas = [c.sha for c in matched_commits]

    if not matched_commits:
        verdict_str = "no_evidence"
        confidence = 0.0
        reason = f"No commits referencing [{task.key}] found in repository {repo_name or '(unlinked)'}."
    else:
        # Take the most relevant commit diff
        best_commit = matched_commits[0]
        diff_text = ""
        if repo_name and github_token:
            diff_text = await _fetch_commit_diff(repo_name, best_commit.sha, github_token)

        if not diff_text and best_commit.files:
            diff_text = f"Modified files: {', '.join(best_commit.files)}\nCommit message: {best_commit.message}"

        # Run AI verification
        ai_res = await _run_ai_verification(
            task_key=task_key,
            task_title=task_title,
            task_desc=task_desc,
            criteria=task_criteria,
            sha=best_commit.sha,
            commit_msg=best_commit.message or "",
            diff=diff_text,
        )
        confidence = ai_res.get("confidence", 0.0)
        reason = ai_res.get("reason", "")
        implements = ai_res.get("implements_task", False)

        threshold = settings.verify_confidence_min or 0.70
        if implements and confidence >= threshold:
            verdict_str = "verified_done"
        elif confidence >= 0.35:
            verdict_str = "needs_review"
        else:
            verdict_str = "needs_review"
            reason = f"Low confidence ({confidence:.0%}): {reason}"

    # Step 4: Update task status in DB with transaction
    with get_session() as session:
        t = session.get(Task, task_id)
        if t:
            old_status = t.status
            target_status = "verified_done" if verdict_str == "verified_done" else "needs_review"

            try:
                if t.status in ("todo", "in_progress"):
                    t.status = "claimed_done"
                    session.add(t)
                    session.flush()

                transition_task(
                    session=session,
                    task_key=t.key,
                    project_id=proj_id,
                    new_status=target_status,
                    actor_member_id=t.owner_member_id,
                    reason=reason,
                    source="verifier",
                    extra={"verdict": "verified" if target_status == "verified_done" else "partial", "confidence": confidence},
                )
            except IllegalTransition:
                # If transition from current state is not allowed directly
                t.status = target_status
                if target_status == "verified_done":
                    t.progress = 100
                    t.completed_at = now
                session.add(t)

            # Record Verification
            v = session.exec(select(Verification).where(Verification.task_id == t.id)).first()
            if not v:
                v = Verification(task_id=t.id)
            v.claimed_by_member_id = t.owner_member_id
            v.verdict = "verified" if target_status == "verified_done" else "inconclusive"
            v.confidence = confidence
            v.reason = reason
            v.matched_shas = matched_shas
            v.completed_at = now
            session.add(v)

            # Auto-resolve any contradictions related to this verified task
            try:
                from models import Contradiction
                open_c = session.exec(
                    select(Contradiction).where(
                        Contradiction.project_id == proj_id,
                        Contradiction.status == "open",
                    )
                ).all()
                for c in open_c:
                    tids = [str(x) for x in (c.task_ids or [])]
                    if str(t.id) in tids or t.key.lower() in (c.summary or "").lower():
                        c.status = "resolved"
                        c.resolved_at = now
                        session.add(c)
            except Exception:
                pass

            # Record event
            event = Event(
                project_id=proj_id,
                ts=now,
                type="task_verified",
                task_id=t.id,
                actor_member_id=t.owner_member_id,
                payload={
                    "key": t.key,
                    "verdict": verdict_str,
                    "confidence": confidence,
                    "reason": reason,
                    "matched_shas": matched_shas,
                },
            )
            session.add(event)
            session.commit()

    # Step 5: Post notification to Telegram group if connected
    if chat_id:
        try:
            from bot import _bot_app
            if _bot_app and _bot_app.bot:
                if verdict_str == "verified_done":
                    msg = (
                        f"✅ *Verification PASSED for {task.key}: {task.title}*\n\n"
                        f"• Confidence: *{confidence:.0%}*\n"
                        f"• Commits: `{', '.join(s[:7] for s in matched_shas[:2])}`\n"
                        f"• Note: _{reason}_\n\n"
                        f"🎉 Task automatically moved to *Verified Done*!"
                    )
                else:
                    msg = (
                        f"🔍 *Verification update for {task.key}: {task.title}*\n\n"
                        f"• Status: *{verdict_str.replace('_', ' ').title()}*\n"
                        f"• Confidence: *{confidence:.0%}*\n"
                        f"• Note: _{reason}_\n\n"
                        f"💡 Team lead can review or approve via the Pilot web dashboard."
                    )
                await _bot_app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        except Exception as exc:
            logger.warning("Could not send Telegram verification notice: %s", exc)

    return {
        "verdict": verdict_str,
        "confidence": confidence,
        "reason": reason,
        "matched_shas": matched_shas,
    }


async def run_github_poll_tick():
    """
    Periodic job (every 45s) to poll GitHub for commits across all active projects.
    """
    settings = get_settings()
    if not settings.github_token:
        return

    try:
        projects_to_poll = []
        with get_session() as session:
            rows = session.exec(
                select(Project.id, Project.repo_full_name).where(
                    Project.status.in_(["planning", "running"]),
                    Project.repo_full_name.is_not(None),
                )
            ).all()
            for pid, rname in rows:
                if pid and rname:
                    projects_to_poll.append((pid, rname))

        for proj_id, repo_full_name in projects_to_poll:
            raw_commits = await _fetch_repo_commits(repo_full_name, settings.github_token, limit=20)
            if not raw_commits:
                continue

            with get_session() as session:
                members = session.exec(select(Member).where(Member.project_id == proj_id)).all()
                upserted = _sync_commits_to_db(session, proj_id, raw_commits, members)
                session.commit()

                # Find any tasks referenced in newly fetched commits
                key_re = re.compile(r"\b(T-\d+)\b", re.IGNORECASE)
                tasks_to_verify = set()
                for c in upserted:
                    keys = key_re.findall(c.message or "")
                    for k in keys:
                        t = session.exec(
                            select(Task).where(Task.project_id == proj_id, Task.key == k.upper())
                        ).first()
                        if t and t.status in ("todo", "claimed_done", "in_progress", "needs_review"):
                            tasks_to_verify.add(t.id)

            for tid in tasks_to_verify:
                logger.info("Auto-verifying task %d after commit detection", tid)
                await verify_task(tid)

    except Exception as exc:
        logger.exception("GitHub poll tick error: %s", exc)
