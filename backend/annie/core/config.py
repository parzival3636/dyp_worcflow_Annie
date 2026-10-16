from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""
    github_username: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    completion_threshold: int = 85


@lru_cache()
def get_settings() -> Settings:
    return Settings()
