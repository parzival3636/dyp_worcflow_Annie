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

    # Annie – GitHub / Supabase / Gemini Verification Pipeline
    github_token: str = ""
    github_webhook_secret: str = ""
    github_username: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"
    completion_threshold: int = 85

    # Uppercase aliases for compatibility across modules
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return self.telegram_bot_token

    @property
    def LLM_BASE_URL(self) -> str:
        return self.llm_base_url

    @property
    def LLM_API_KEY(self) -> str:
        return self.llm_api_key

    @property
    def LLM_MODEL(self) -> str:
        return self.llm_model

    @property
    def LLM_FALLBACK_MODEL(self) -> str:
        return self.llm_fallback_model

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url

    @property
    def CHECKIN_HOURS(self) -> int:
        return self.checkin_hours

    @property
    def DEMO_MODE(self) -> bool:
        return self.demo_mode

    @property
    def QUIET_HOURS_START(self) -> int:
        return self.quiet_hours_start

    @property
    def QUIET_HOURS_END(self) -> int:
        return self.quiet_hours_end

    @property
    def FRONTEND_ORIGIN(self) -> str:
        return "http://localhost:5173"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton accessor – created on first call."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


class _LazySettings:
    def __getattr__(self, name):
        return getattr(get_settings(), name)


settings = _LazySettings()
