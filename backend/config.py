"""
Pilot – configuration loaded once from .env via pydantic-settings.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str
    bot_username: str = ""           # e.g. "pilot_coordinator_bot" (without @)

    # LLM
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_fallback_model: str = ""

    # Database (Supabase Postgres – session pooler port 5432 or direct)
    database_url: str
    database_url_test: str = ""     # local docker Postgres for tests

    # SMTP (optional – if unset, invite links are logged to console only)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Auth & Security
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_A_LONG_RANDOM_STRING"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7   # 7 days
    frontend_url: str = "https://worcflow-frontend.vercel.app"

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""
    github_owner: str = ""          # GitHub org/user that owns created repos
    github_username: str = ""       # legacy alias kept for compatibility
    github_poll_seconds: int = 45

    # Verification
    verify_confidence_min: float = 0.7   # threshold for verified_done
    verify_mode: str = "soft"            # soft | strict (legacy)

    # Scheduler / behaviour
    checkin_hours: int = 4
    checkin_minutes: int = 2         # Periodic check-in interval in minutes (default 2 for rapid reviews)
    demo_mode: bool = False
    quiet_hours_start: int = 22
    quiet_hours_end: int = 8
    group_debounce_seconds: int = 12
    group_max_buffer: int = 6
    llm_log_path: str = "docs/demo-evidence/llm.log"

    # Annie legacy compatibility (kept to avoid import errors from existing modules)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"
    completion_threshold: int = 85

    # Uppercase property aliases for compatibility across modules
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return self.telegram_bot_token

    @property
    def BOT_USERNAME(self) -> str:
        return self.bot_username

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
        return self.frontend_url

    @property
    def jwt_secret_key(self) -> str:
        """Alias kept for compatibility with existing auth.py code."""
        return self.secret_key

    @property
    def GITHUB_OWNER(self) -> str:
        return self.github_owner or self.github_username

    @property
    def VERIFY_CONFIDENCE_MIN(self) -> float:
        return self.verify_confidence_min


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
