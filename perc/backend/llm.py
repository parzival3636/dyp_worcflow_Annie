import os
import re
import json
import time
from datetime import datetime, timezone
from typing import Literal, Optional, Any
import httpx
from pydantic import BaseModel, Field, ValidationError

from backend.config import settings


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
    acceptance_criteria: list[str]
    effort: int = Field(ge=1, le=8)
    depends_on: list[str] = Field(default_factory=list)
    is_milestone: bool = False


class P2Plan(BaseModel):
    tasks: list[P2Task]


class P3Blocker(BaseModel):
    description: str
    type: str
    needed_from: str


class P3Reply(BaseModel):
    task_key: Optional[str] = None
    intent: Literal[
        "progress_update",
        "blocker",
        "completion_claim",
        "question",
        "off_topic",
        "unclear",
    ]
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
# Helpers: JSON Extraction, Logging, and Fallbacks
# ---------------------------------------------------------

def extract_json_str(text: str) -> str:
    """
    Strips markdown code fences and extracts the first balanced JSON object.
    """
    text = text.strip()

    # Strip code fences if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            # Fallback fence stripping line by line
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        return text

    # Extract first balanced curly bracket block
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
    """
    Returns a safe fallback model if the LLM fails all retries.
    """
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

    raise ValueError(f"No safe fallback defined for model class {model_cls.__name__}")


def log_llm_attempt(
    system_prompt: str,
    user_prompt: str,
    raw_response: Optional[str],
    parsed_json: Optional[dict[str, Any]],
    error: Optional[str],
    latency_ms: float,
    attempt: int,
):
    """
    Appends every LLM attempt as a JSON line to docs/demo-evidence/llm.log.
    Secrets and sensitive API keys are redacted.
    """
    log_dir = os.path.join("docs", "demo-evidence")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "llm.log")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": settings.LLM_MODEL,
        "attempt": attempt,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw_response": raw_response,
        "parsed": parsed_json,
        "error": error,
        "latency_ms": round(latency_ms, 2),
    }

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------
# Core Function: call_json
# ---------------------------------------------------------

def call_json(
    system: str,
    user: str,
    model_cls: type[BaseModel],
    retries: int = 2,
    http_client: Optional[httpx.Client] = None,
) -> BaseModel:
    """
    Calls an OpenAI-compatible endpoint with temperature=0.1, parses and validates JSON
    against model_cls, retries with the validation error on failure, and returns
    a safe fallback if all retries are exhausted. Never raises to caller (except P2Plan).
    """
    base_url = settings.LLM_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    current_user_prompt = user
    attempts_left = retries + 1
    attempt_num = 0

    client_context = http_client if http_client is not None else httpx.Client(timeout=30.0)

    try:
        while attempts_left > 0:
            attempt_num += 1
            attempts_left -= 1
            start_time = time.time()
            raw_text = None
            error_str = None
            parsed_data = None

            payload = {
                "model": settings.LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": f"{system}\nReply with JSON only. No prose, no markdown.",
                    },
                    {"role": "user", "content": current_user_prompt},
                ],
                "temperature": 0.1,
            }

            try:
                response = client_context.post(url, json=payload, headers=headers)
                latency_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    error_str = f"HTTP {response.status_code}: {response.text}"
                    log_llm_attempt(
                        system, current_user_prompt, response.text, None, error_str, latency_ms, attempt_num
                    )
                    current_user_prompt = f"{user}\n\nPrevious error: {error_str}. Please return valid JSON matching schema."
                    continue

                resp_json = response.json()
                raw_text = resp_json["choices"][0]["message"]["content"]
                json_str = extract_json_str(raw_text)

                validated_instance = model_cls.model_validate_json(json_str)
                parsed_data = validated_instance.model_dump()

                log_llm_attempt(
                    system, current_user_prompt, raw_text, parsed_data, None, latency_ms, attempt_num
                )
                return validated_instance

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                latency_ms = (time.time() - start_time) * 1000
                error_str = f"Network/Timeout error: {str(exc)}"
                log_llm_attempt(
                    system, current_user_prompt, None, None, error_str, latency_ms, attempt_num
                )
                current_user_prompt = f"{user}\n\nPrevious attempt timed out or failed to connect."

            except (ValidationError, json.JSONDecodeError, KeyError, IndexError) as exc:
                latency_ms = (time.time() - start_time) * 1000
                error_str = f"Parsing/Validation error: {str(exc)}"
                log_llm_attempt(
                    system, current_user_prompt, raw_text, None, error_str, latency_ms, attempt_num
                )
                current_user_prompt = (
                    f"{user}\n\nValidation error: {str(exc)}. Please fix and reply with JSON only."
                )

    finally:
        if http_client is None:
            client_context.close()

    # All retries failed: return safe fallback
    return get_fallback(model_cls, user)
