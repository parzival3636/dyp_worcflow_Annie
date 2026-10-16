from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    TELEGRAM_BOT_TOKEN: str = ""
    GITHUB_TOKEN: str = ""
    GITHUB_OWNER: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    CHECKIN_HOURS: int = 4
    DEMO_MODE: bool = False
    QUIET_HOURS_START: int = 22
    QUIET_HOURS_END: int = 8
    FRONTEND_ORIGIN: str = "http://localhost:5173"


settings = Settings()
