"""
Base Protocol for Transcript Providers.
"""
from __future__ import annotations

from typing import Protocol, Any, List, Optional
from pydantic import BaseModel


class DispatchResult(BaseModel):
    success: bool
    detail: Optional[str] = None


class ProviderSentence(BaseModel):
    index: int
    speaker_name: str
    speaker_id: Optional[str] = None
    text: str
    start_time: float
    end_time: float


class ProviderTranscript(BaseModel):
    id: str
    title: Optional[str] = None
    date: Optional[Any] = None
    duration: Optional[float] = None
    participants: List[str] = []
    speakers: List[dict] = []
    sentences: List[ProviderSentence] = []
    summary: Optional[dict] = None


class ProviderTranscriptSummary(BaseModel):
    id: str
    title: Optional[str] = None
    date: Optional[Any] = None
    meeting_link: Optional[str] = None


class TranscriptProvider(Protocol):
    async def dispatch_bot(self, link: str, client_reference_id: str) -> DispatchResult:
        ...

    async def fetch_transcript(self, provider_meeting_id: str) -> Optional[ProviderTranscript]:
        ...

    async def list_recent(self, limit: int = 10) -> List[ProviderTranscriptSummary]:
        ...
