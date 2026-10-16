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
        raise PlanGenerationError("Failed to generate task plan after retries")

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
    Returns an AwaitableModelWrapper so it can be called synchronously:
        res = call_json(...)
        print(res.title)
    OR asynchronously:
        res = await call_json(...)
    """
    cfg = get_settings()
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

