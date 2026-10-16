"""
Pilot – configuration loaded once from .env via pydantic-settings.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str

    # LLM
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_fallback_model: str = ""

    # Database (Supabase Postgres via Session pooler or Direct)
    database_url: str

    # Scheduler / behaviour
    checkin_hours: int = 4
    demo_mode: bool = False
    verify_mode: str = "soft"          # soft | strict
    quiet_hours_start: int = 22
    quiet_hours_end: int = 8
    group_debounce_seconds: int = 12
    group_max_buffer: int = 6

    # Logging
    llm_log_path: str = "docs/demo-evidence/llm.log"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton accessor – created on first call."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
