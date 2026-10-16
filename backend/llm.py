"""
Pilot – LLM client.

async call_json(system, user, model_cls, retries=2):
  • temperature 0.1, JSON-only instruction
  • strip markdown fences, validate with Pydantic
  • on validation failure retry with error appended
  • after retries try LLM_FALLBACK_MODEL once
  • then return a safe default (never raise)
  • 30 s timeout, async httpx
  • logs prompt / response / latency to LLM_LOG_PATH
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from config import get_settings

logger = logging.getLogger("pilot.llm")

T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _log_llm(prompt_system: str, prompt_user: str, response: str, latency: float, model: str, error: str | None = None):
    """Append one JSON-lines entry to the LLM log file."""
    settings = get_settings()
    log_path = Path(settings.llm_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": model,
        "latency_s": round(latency, 3),
        "system_prompt_len": len(prompt_system),
        "user_prompt_len": len(prompt_user),
        "response_len": len(response),
    }
    if error:
        entry["error"] = error
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        logger.warning("Failed to write LLM log", exc_info=True)


async def _raw_chat(
    system: str,
    user: str,
    model: str,
    base_url: str,
    api_key: str,
) -> str:
    """Send a chat completion request and return the raw text content."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def call_json(
    system: str,
    user: str,
    model_cls: Type[T],
    retries: int = 2,
) -> T:
    """
    Call the LLM asking for JSON matching *model_cls*.

    Retry on validation failure (appending the error to the user prompt).
    After *retries* tries on the primary model, try the fallback model once.
    If everything fails, return a **safe default** using model_cls.model_construct().

    NEVER raises into a handler.
    """
    settings = get_settings()
    json_instruction = (
        "\n\nIMPORTANT: Reply ONLY with valid JSON matching this schema, no prose, "
        "no markdown fences:\n" + json.dumps(model_cls.model_json_schema(), indent=2)
    )
    full_system = system + json_instruction

    models_to_try: list[str] = [settings.llm_model] * retries
    if settings.llm_fallback_model:
        models_to_try.append(settings.llm_fallback_model)

    current_user = user
    last_error: str | None = None

    for i, model in enumerate(models_to_try):
        t0 = time.monotonic()
        raw = ""
        try:
            raw = await _raw_chat(full_system, current_user, model, settings.llm_base_url, settings.llm_api_key)
            latency = time.monotonic() - t0
            _log_llm(full_system, current_user, raw, latency, model)

            cleaned = _strip_fences(raw)
            result = model_cls.model_validate_json(cleaned)
            return result

        except ValidationError as ve:
            latency = time.monotonic() - t0
            last_error = str(ve)
            _log_llm(full_system, current_user, raw, latency, model, error=last_error)
            logger.warning("LLM JSON validation failed (attempt %d): %s", i + 1, last_error[:200])
            # Append error for next retry
            current_user = user + f"\n\n[Previous response had a validation error: {last_error}. Please fix and reply with valid JSON only.]"

        except Exception as exc:
            latency = time.monotonic() - t0
            last_error = str(exc)
            _log_llm(full_system, current_user, raw, latency, model, error=last_error)
            logger.warning("LLM call failed (attempt %d): %s", i + 1, last_error[:200])

    # All attempts exhausted → safe default
    logger.error("LLM exhausted all attempts. Returning safe default for %s", model_cls.__name__)
    return _safe_default(model_cls)


def _safe_default(model_cls: Type[T]) -> T:
    """
    Build a 'safe' instance of model_cls that does nothing harmful.
    Uses model_construct() with sensible zero-values.
    """
    # Build kwargs from field defaults and annotations
    defaults: dict = {}
    for name, field_info in model_cls.model_fields.items():
        if field_info.default is not None:
            defaults[name] = field_info.default
        else:
            anno = field_info.annotation
            if anno is str or anno == str:
                defaults[name] = ""
            elif anno is int or anno == int:
                defaults[name] = 0
            elif anno is float or anno == float:
                defaults[name] = 0.0
            elif anno is bool or anno == bool:
                defaults[name] = False
            elif anno is list or (hasattr(anno, "__origin__") and getattr(anno, "__origin__", None) is list):
                defaults[name] = []
            else:
                defaults[name] = None

    # Override known fields for safety
    if "intent" in defaults:
        defaults["intent"] = "unclear"
    if "needs_clarification" in defaults:
        defaults["needs_clarification"] = True
    if "confidence" in defaults:
        defaults["confidence"] = 0.0
    if "kind" in defaults:
        defaults["kind"] = "none"
    if "observations" in defaults:
        defaults["observations"] = []

    return model_cls.model_construct(**defaults)
