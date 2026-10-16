"""
Fireflies GraphQL API Provider.
Client for dispatching notetaker bots and fetching completed transcripts.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.providers.base import (
    DispatchResult,
    ProviderSentence,
    ProviderTranscript,
    ProviderTranscriptSummary,
    TranscriptProvider,
)

logger = logging.getLogger("transcribe.fireflies")

# VERIFY against current Fireflies docs
ADD_BOT_MUTATION = """
mutation AddBot($link: String!) {
  addToLiveMeeting(meeting_link: $link) {
    success
  }
}
"""

# VERIFY against current Fireflies docs
GET_TRANSCRIPT_QUERY = """
query GetTranscript($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    participants
    speakers {
      id
      name
    }
    sentences {
      index
      speaker_name
      speaker_id
      text
      start_time
      end_time
    }
    summary {
      overview
      action_items
      keywords
    }
  }
}
"""

# VERIFY against current Fireflies docs
RECENT_TRANSCRIPTS_QUERY = """
query Recent($limit: Int) {
  transcripts(limit: $limit) {
    id
    title
    date
    meeting_link
  }
}
"""


class ProviderError(Exception):
    def __init__(self, message: str, code: str = "PROVIDER_ERROR", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class FirefliesProvider:
    """Fireflies.ai GraphQL Client implementing TranscriptProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.FIREFLIES_API_KEY
        self.api_url = api_url or settings.FIREFLIES_API_URL
        self._external_client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client:
            return self._external_client
        return httpx.AsyncClient(
            timeout=15.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def _execute_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query/mutation with 3 retries on 5xx or network errors."""
        payload = {"query": query, "variables": variables or {}}
        retries = 3
        backoff = 0.5

        for attempt in range(1, retries + 1):
            client = self._get_client()
            try:
                resp = await client.post(self.api_url, json=payload)
                if resp.status_code == 401 or resp.status_code == 403:
                    raise ProviderError("Authentication failed with Fireflies API.", code="AUTH", retryable=False)
                if resp.status_code == 429:
                    raise ProviderError("Rate limit exceeded on Fireflies API.", code="RATE_LIMIT", retryable=True)
                if resp.status_code >= 500:
                    if attempt == retries:
                        raise ProviderError(f"Fireflies API server error: {resp.status_code}", code="SERVER_ERROR", retryable=True)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                resp.raise_for_status()
                data = resp.json()

                if "errors" in data and data["errors"]:
                    err_msg = "; ".join(e.get("message", "Unknown error") for e in data["errors"])
                    if "rate limit" in err_msg.lower():
                        raise ProviderError(err_msg, code="RATE_LIMIT", retryable=True)
                    raise ProviderError(err_msg, code="GRAPHQL_ERROR", retryable=False)

                return data.get("data", {})

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt == retries:
                    raise ProviderError(f"Network error calling Fireflies: {exc}", code="NETWORK_ERROR", retryable=True)
                await asyncio.sleep(backoff)
                backoff *= 2
            finally:
                if not self._external_client:
                    await client.aclose()

        raise ProviderError("Failed to execute Fireflies GraphQL call after retries.", code="UNKNOWN", retryable=False)

    async def dispatch_bot(self, link: str, client_reference_id: str) -> DispatchResult:
        """Call addToLiveMeeting mutation."""
        data = await self._execute_graphql(ADD_BOT_MUTATION, variables={"link": link})
        add_result = data.get("addToLiveMeeting", {})
        success = bool(add_result.get("success", False))
        return DispatchResult(success=success)

    async def fetch_transcript(self, provider_meeting_id: str) -> Optional[ProviderTranscript]:
        """Fetch transcript by Fireflies ID. Returns None if transcript is not ready."""
        data = await self._execute_graphql(GET_TRANSCRIPT_QUERY, variables={"id": provider_meeting_id})
        t_data = data.get("transcript")
        if not t_data:
            return None

        raw_sentences = t_data.get("sentences")
        if not raw_sentences or len(raw_sentences) == 0:
            return None

        sentences: List[ProviderSentence] = []
        for s in raw_sentences:
            sentences.append(
                ProviderSentence(
                    index=s.get("index", 0),
                    speaker_name=s.get("speaker_name", "Unknown"),
                    speaker_id=str(s.get("speaker_id") or ""),
                    text=s.get("text", "").strip(),
                    start_time=float(s.get("start_time", 0.0)),
                    end_time=float(s.get("end_time", 0.0)),
                )
            )

        return ProviderTranscript(
            id=t_data["id"],
            title=t_data.get("title"),
            date=t_data.get("date"),
            duration=t_data.get("duration"),
            participants=t_data.get("participants", []),
            speakers=t_data.get("speakers", []),
            sentences=sentences,
            summary=t_data.get("summary"),
        )

    async def list_recent(self, limit: int = 10) -> List[ProviderTranscriptSummary]:
        """List recent transcripts for polling fallback."""
        data = await self._execute_graphql(RECENT_TRANSCRIPTS_QUERY, variables={"limit": limit})
        transcripts = data.get("transcripts", [])
        return [
            ProviderTranscriptSummary(
                id=item["id"],
                title=item.get("title"),
                date=item.get("date"),
                meeting_link=item.get("meeting_link"),
            )
            for item in transcripts
        ]
