from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
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

    class Config:
        env_file = ("../.env", ".env", "../../.env")
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
