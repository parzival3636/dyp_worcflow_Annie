"""
Pilot – LLM client and schemas.
Supports both synchronous calls (for Planner, Guide, Ripple, Contradiction, Routing)
and asynchronous calls (for Telegram bot DM interpretation, group chat extraction, etc.)
via AwaitableModelWrapper.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

try:
    from config import get_settings, settings
except ImportError:
    from backend.config import get_settings, settings

logger = logging.getLogger("pilot.llm")

T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


class PlanGenerationError(Exception):
    """Raised when plan generation fails even after retries."""
    pass


# ---------------------------------------------------------
# Pydantic Output Models (P1 - P6)
# ---------------------------------------------------------

class P1Project(BaseModel):
    name: str
    summary: str
    duration_hours: int = 20


class P2Task(BaseModel):
    title: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    effort: int = Field(default=3, ge=1, le=8)
    depends_on: list[str] = Field(default_factory=list)
    is_milestone: bool = False


class P2Plan(BaseModel):
    tasks: list[P2Task]


class P3Blocker(BaseModel):
    description: str
    type: str = "other"
    needed_from: str = ""


class P3Reply(BaseModel):
    task_key: Optional[str] = None
    intent: Literal[
        "progress_update",
        "blocker",
        "completion_claim",
        "question",
        "off_topic",
        "unclear",
    ] = "unclear"
    new_status: Optional[str] = None
    progress: Optional[int] = None
    blocker: Optional[P3Blocker] = None
    claims_about_others: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarifying_question: Optional[str] = None
    confidence: float = 0.0


class P4Criterion(BaseModel):
    criterion: str
    met: bool
    note: str


class P4Verdict(BaseModel):
    verdict: Literal["verified", "partial", "no_evidence"]
    confidence: float
    matched_shas: list[str] = Field(default_factory=list)
    criteria_results: list[P4Criterion] = Field(default_factory=list)
    reason: str


class P5Contradiction(BaseModel):
    has_contradiction: bool
    summary: str = ""
    task_ids: list[str] = Field(default_factory=list)
    member_ids: list[int] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)


class P6Route(BaseModel):
    member_id: int
    reason: str


# ---------------------------------------------------------
# Dual Sync/Async Awaitable Wrapper
# ---------------------------------------------------------

class AwaitableModelWrapper:
    """
    Wraps a Pydantic model instance so that:
    1. Synchronous callers can access fields directly: wrapper.tasks, wrapper.member_id
    2. Asynchronous callers can await it: await wrapper -> returns inner model
    """
    def __init__(self, inner: Any):
        object.__setattr__(self, "_inner", inner)

    def __await__(self):
        async def _coro():
            return object.__getattribute__(self, "_inner")
        return _coro().__await__()

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_inner"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(object.__getattribute__(self, "_inner"), name, value)

    def __getitem__(self, item: Any) -> Any:
        return object.__getattribute__(self, "_inner")[item]

    def __iter__(self):
        return iter(object.__getattribute__(self, "_inner"))

    def __repr__(self) -> str:
        return repr(object.__getattribute__(self, "_inner"))


# ---------------------------------------------------------
# JSON Extraction, Logging, and Fallbacks
# ---------------------------------------------------------

def extract_json_str(text: str) -> str:
    """Strips markdown code fences and extracts the first balanced JSON object."""
    text = text.strip()
    if "```" in text:
        match = _FENCE_RE.search(text)
        if match:
            text = match.group(1).strip()
        else:
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        return text

    first_brace = text.find("{")
    if first_brace != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(first_brace, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return text[first_brace : i + 1]

    return text


def get_fallback(model_cls: type[BaseModel], user_prompt: str) -> BaseModel:
    """Returns a safe fallback model if the LLM fails all retries."""
    if issubclass(model_cls, P3Reply):
        return P3Reply(
            intent="unclear",
            needs_clarification=True,
            clarifying_question="Could you tell me a bit more about where this task stands?",
            confidence=0.0,
        )
    elif issubclass(model_cls, P4Verdict):
        return P4Verdict(
            verdict="no_evidence",
            confidence=0.0,
            matched_shas=[],
            criteria_results=[],
            reason="Verifier unavailable",
        )
    elif issubclass(model_cls, P5Contradiction):
        return P5Contradiction(has_contradiction=False)
    elif issubclass(model_cls, P6Route):
        return P6Route(member_id=1, reason="Fallback to lead")
    elif issubclass(model_cls, P1Project):
        clean_name = user_prompt.strip()[:40] or "Project"
        return P1Project(name=clean_name, summary="Project generated via fallback", duration_hours=20)
    elif issubclass(model_cls, P2Plan):
        return _generate_fallback_plan(user_prompt)

    # Generic fallback using field defaults
    defaults = {}
    for name, field_info in model_cls.model_fields.items():
        if field_info.default_factory is not None:
            defaults[name] = field_info.default_factory()
        elif field_info.default is not None:
            defaults[name] = field_info.default
        else:
            defaults[name] = None
    return model_cls.model_construct(**defaults)


def _generate_fallback_plan(user_prompt: str) -> P2Plan:
    name = "Platform"
    for line in user_prompt.splitlines():
        if line.lower().startswith("project name:"):
            name = line.split(":", 1)[1].strip() or "Platform"
            break

    t1 = P2Task(
        title=f"Setup Relational Database & Migrations for {name}",
        description=f"Design SQLModel schema, indexes, and initial migrations for {name}.",
        acceptance_criteria=[
            "Relational models defined with primary keys and constraints",
            "Initial database migration runs with zero schema errors",
        ],
        effort=3,
        depends_on=[],
        is_milestone=False,
    )
    t2 = P2Task(
        title="Authentication & Role-Based Security Guard",
        description="Implement JWT session token issue, verification, and route security guards.",
        acceptance_criteria=[
            "JWT token generation and verification endpoints operational",
            "Unauthorized requests return HTTP 401 Unauthorized",
        ],
        effort=2,
        depends_on=[t1.title],
        is_milestone=False,
    )
    t3 = P2Task(
        title=f"Core Data Service & Business Logic Layer",
        description=f"Implement backend services, domain repositories, and data handlers for {name}.",
        acceptance_criteria=[
            "Business logic validated with comprehensive unit tests",
            "CRUD operations persist cleanly to Postgres",
        ],
        effort=5,
        depends_on=[t1.title],
        is_milestone=False,
    )
    t4 = P2Task(
        title="REST API Endpoints & Contract Validation",
        description=f"Expose typed REST endpoints for {name} with Pydantic request and response schemas.",
        acceptance_criteria=[
            "Endpoints conform to OpenAPI schema",
            "Invalid payloads return HTTP 422 with validation errors",
        ],
        effort=4,
        depends_on=[t2.title, t3.title],
        is_milestone=False,
    )
    t5 = P2Task(
        title="Event Pipeline & Telegram Webhook Processor",
        description="Implement asynchronous event queue and telemetry listener for live chat sync.",
        acceptance_criteria=[
            "Events ingested and persisted without blocking the web event loop",
            "Dead-letter retry queue catches transient network drops",
        ],
        effort=3,
        depends_on=[t4.title],
        is_milestone=False,
    )
    t6 = P2Task(
        title="Automated Test Suite & AST Proof Verifiers",
        description="Write unit, integration, and commit verification tests for the core workflow.",
        acceptance_criteria=[
            "Automated test runner achieves green exit code",
            "AST verifier accurately maps git diffs to task criteria",
        ],
        effort=3,
        depends_on=[t4.title],
        is_milestone=False,
    )
    t7 = P2Task(
        title="Interactive Frontend Workspace & Kanban Sync",
        description="Build responsive user interfaces, real-time polling hooks, and task drag-and-drop.",
        acceptance_criteria=[
            "Task board renders live states from backend API",
            "Optimistic updates transition cards instantly with toast notifications",
        ],
        effort=5,
        depends_on=[t4.title],
        is_milestone=False,
    )
    t8 = P2Task(
        title=f"End-to-End System Demo & Verification Milestone",
        description=f"Verify end-to-end user journeys for {name} with live proof-of-work validation.",
        acceptance_criteria=[
            "Full end-to-end flow verified from coordination bot to UI board",
            "Zero console errors or unhandled promise rejections during demo",
        ],
        effort=3,
        depends_on=[t5.title, t6.title, t7.title],
        is_milestone=True,
    )
    return P2Plan(tasks=[t1, t2, t3, t4, t5, t6, t7, t8])


def _try_gemini_call(full_system: str, user_prompt: str, model_cls: Type[T]) -> Optional[T]:
    """Attempt call to Google Gemini with structured outputs and fallback models."""
    cfg = get_settings()
    api_key = cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        models_to_try = [
            cfg.gemini_model,
            "gemini-flash-lite-latest",
            "gemini-3.8-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
        ]
        models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))
        prompt_content = f"{full_system}\n\nTask/Input:\n{user_prompt}"

        for model_name in models_to_try:
            try:
                # 1. Native structured output with response_schema
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt_content,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_schema=model_cls,
                    ),
                )
                if resp and resp.text:
                    cleaned = extract_json_str(resp.text)
                    return model_cls.model_validate_json(cleaned)
            except Exception as schema_exc:
                logger.debug("Gemini response_schema on %s failed: %s, trying JSON mode", model_name, schema_exc)
                try:
                    # 2. JSON mode without strict response_schema
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                    )
                    if resp and resp.text:
                        cleaned = extract_json_str(resp.text)
                        return model_cls.model_validate_json(cleaned)
                except Exception as inner_exc:
                    logger.warning("Gemini model %s failed: %s", model_name, inner_exc)
                    continue

    except Exception as exc:
        logger.warning("Gemini LLM call encountered error: %s", exc)
    return None


def _log_llm(
    system_prompt: str,
    user_prompt: str,
    raw_response: Optional[str],
    latency_s: float,
    model: str,
    error: Optional[str] = None,
):
    cfg = get_settings()
    log_dir = os.path.dirname(cfg.llm_log_path) or "docs/demo-evidence"
    os.makedirs(log_dir, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "latency_s": round(latency_s, 3),
        "system_prompt_len": len(system_prompt),
        "user_prompt_len": len(user_prompt),
        "raw_response": raw_response[:500] if raw_response else None,
        "error": error,
    }
    try:
        with open(cfg.llm_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------
# Core Function: call_json (Dual Sync/Async)
# ---------------------------------------------------------

def call_json(
    system: str,
    user: str,
    model_cls: Type[T],
    retries: int = 2,
    http_client: Optional[httpx.Client] = None,
) -> Any:
    """
    Calls LLM asking for JSON matching model_cls.
    Supports Google Gemini directly or OpenAI-compatible endpoint.
    Returns an AwaitableModelWrapper so it can be called synchronously:
        res = call_json(...)
        print(res.title)
    OR asynchronously:
        res = await call_json(...)
    """
    cfg = get_settings()

    # If Gemini is configured and local LLM is not a remote endpoint, use Gemini directly
    use_gemini_first = bool(
        cfg.gemini_api_key
        and (not cfg.llm_base_url or "localhost" in cfg.llm_base_url or "127.0.0.1" in cfg.llm_base_url)
    )

    if use_gemini_first:
        gemini_res = _try_gemini_call(system, user, model_cls)
        if gemini_res is not None:
            return AwaitableModelWrapper(gemini_res)

    base_url = (cfg.llm_base_url or "http://localhost:11434/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if cfg.llm_api_key:
        headers["Authorization"] = f"Bearer {cfg.llm_api_key}"

    json_instruction = (
        "\n\nReply ONLY with valid JSON matching this schema, no prose, no markdown:\n"
        + json.dumps(model_cls.model_json_schema(), indent=2)
    )
    full_system = system + json_instruction
    current_user_prompt = user

    client = http_client if http_client is not None else httpx.Client(timeout=8.0)
    attempts_left = retries + 1

    try:
        while attempts_left > 0:
            attempts_left -= 1
            start_time = time.monotonic()
            raw_text = None
            error_str = None

            payload = {
                "model": cfg.llm_model,
                "messages": [
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": current_user_prompt},
                ],
                "temperature": 0.1,
            }

            try:
                resp = client.post(url, json=payload, headers=headers)
                latency = time.monotonic() - start_time

                if resp.status_code != 200:
                    error_str = f"HTTP {resp.status_code}: {resp.text}"
                    _log_llm(full_system, current_user_prompt, resp.text, latency, cfg.llm_model, error=error_str)
                    current_user_prompt = f"{user}\n\nPrevious error: {error_str}. Fix and return valid JSON only."
                    continue

                resp_json = resp.json()
                raw_text = resp_json["choices"][0]["message"]["content"]
                cleaned = extract_json_str(raw_text)
                validated = model_cls.model_validate_json(cleaned)
                _log_llm(full_system, current_user_prompt, raw_text, latency, cfg.llm_model)
                return AwaitableModelWrapper(validated)

            except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as exc:
                latency = time.monotonic() - start_time
                error_str = f"Network error: {str(exc)}"
                _log_llm(full_system, current_user_prompt, None, latency, cfg.llm_model, error=error_str)
                # If connection refused or offline, don't waste time retrying
                break

            except (ValidationError, json.JSONDecodeError, KeyError, IndexError) as exc:
                latency = time.monotonic() - start_time
                error_str = f"Validation/Parsing error: {str(exc)}"
                _log_llm(full_system, current_user_prompt, raw_text, latency, cfg.llm_model, error=error_str)
                current_user_prompt = f"{user}\n\n[Validation error: {error_str}. Please fix and reply with JSON only.]"

    finally:
        if http_client is None:
            client.close()

    # Try Gemini if local endpoint failed and not already tried
    if not use_gemini_first:
        gemini_res = _try_gemini_call(full_system, user, model_cls)
        if gemini_res is not None:
            return AwaitableModelWrapper(gemini_res)

    # Fallback if exhausted
    fallback = get_fallback(model_cls, user)
    return AwaitableModelWrapper(fallback)


def _safe_default(model_cls: type) -> Any:
    """Safe fallback when LLM parsing/network fails."""
    try:
        return model_cls()
    except Exception:
        try:
            return model_cls(results=[])
        except Exception:
            return get_fallback(model_cls, "")

