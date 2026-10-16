"""
FastAPI dependency injection utilities for DB session, providers, LLM client, and notifiers.
"""
from __future__ import annotations

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.integrations.members import InMemoryMemberRepository, MemberRepository
from app.integrations.tasks import InMemoryTaskSink, TaskSink
from app.llm.client import FakeLLMClient, HttpLLMClient, LLMClient
from app.providers.base import DispatchResult, TranscriptProvider
from app.providers.fireflies import FirefliesProvider
from app.services.notifier import FakeNotifier, Notifier, TelegramNotifier


class DefaultMockProvider:
    async def dispatch_bot(self, link: str, client_ref_id: str) -> DispatchResult:
        return DispatchResult(success=True)

    async def fetch_transcript(self, id: str):
        return None

    async def list_recent(self, limit: int = 10):
        return []


def get_session(session: Session = Depends(get_db)) -> Generator[Session, None, None]:
    return session


def get_provider() -> TranscriptProvider:
    settings = get_settings()
    if settings.APP_ENV == "test":
        return DefaultMockProvider()
    return FirefliesProvider()


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.APP_ENV == "test":
        return FakeLLMClient()
    return HttpLLMClient()


def get_notifier() -> Notifier:
    settings = get_settings()
    if settings.APP_ENV == "test":
        return FakeNotifier()
    return TelegramNotifier()


def get_member_repo() -> MemberRepository:
    return InMemoryMemberRepository()
