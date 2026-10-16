"""
LLM client protocol, Real HTTP implementation, and FakeLLMClient for testing.
Supports Groq, OpenAI, and Anthropic.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Protocol

import httpx

from app.config import get_settings

logger = logging.getLogger("transcribe.llm")

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


class ExtractionError(Exception):
    pass


class LLMClient(Protocol):
    async def complete_json(self, system: str, user: str, schema: dict) -> dict:
        ...


class FakeLLMClient:
    """Fake LLM client that returns queued canned JSON responses for hermetic tests."""

    def __init__(self, responses: Optional[List[dict]] = None):
        self.responses: List[dict] = list(responses or [])
        self.call_history: List[Dict[str, Any]] = []

    def queue_response(self, resp: dict):
        self.responses.append(resp)

    async def complete_json(self, system: str, user: str, schema: dict) -> dict:
        self.call_history.append({"system": system, "user": user, "schema": schema})
        if self.responses:
            item = self.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return {"items": [], "meeting_summary": "Empty transcript."}


class HttpLLMClient:
    """Production LLM client calling Groq, OpenAI, or Anthropic endpoints with multi-key pool support."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = model or settings.LLM_MODEL
        
        # Build key pool for Groq (supports 3 keys + fallback)
        if "groq" in self.provider:
            pool = settings.get_groq_keys()
            if api_key and api_key not in pool:
                pool.insert(0, api_key)
            self.api_keys = pool or [settings.LLM_API_KEY]
        else:
            self.api_keys = [api_key or settings.LLM_API_KEY]
        
        self._key_index = 0

    def _next_key(self) -> str:
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index = (self._key_index + 1) % len(self.api_keys)
        return key

    async def complete_json(self, system: str, user: str, schema: dict) -> dict:
        url = "https://api.openai.com/v1/chat/completions"
        if "groq" in self.provider:
            url = "https://api.groq.com/openai/v1/chat/completions"
        elif "anthropic" in self.provider:
            url = "https://api.anthropic.com/v1/messages"

        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system + "\nOutput strictly valid JSON matching the schema."},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }

        # Try available keys in the pool if rate limited
        attempts = len(self.api_keys)
        last_error = None

        for attempt in range(attempts):
            api_key = self._next_key()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            if "anthropic" in self.provider:
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }

            async with httpx.AsyncClient(timeout=45.0) as client:
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 429 and attempt < attempts - 1:
                        logger.warning("Groq key rate limited (%s...). Switching to next key in pool.", api_key[:12])
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    cleaned = _strip_fences(raw_content)
                    return json.loads(cleaned)
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 429 and attempt < attempts - 1:
                        logger.warning("Groq key rate limited. Rotating to next key.")
                        continue
                    raise ExtractionError(f"HTTP error from LLM: {e}")
                except Exception as e:
                    logger.error("Failed to parse JSON: %s", e)
                    raise ExtractionError(f"Failed to parse LLM JSON: {e}")

        if last_error:
            raise ExtractionError(f"All keys in LLM pool exhausted or failed: {last_error}")
        raise ExtractionError("LLM extraction failed after key rotations.")
