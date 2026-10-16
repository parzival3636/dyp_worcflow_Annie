"""
Configuration settings for the transcribe module.
Uses pydantic-settings to read from environment variables or .env file.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    APP_BASE_URL: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite:///./transcribe.db"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    FIREFLIES_API_KEY: str = ""
    FIREFLIES_API_URL: str = "https://api.fireflies.ai/graphql"
    FIREFLIES_WEBHOOK_SECRET: str = ""
    FIREFLIES_BOT_NAME: str = "Pilot Notetaker"

    LLM_PROVIDER: str = "anthropic"
    LLM_API_KEY: str = ""
    GROQ_API_KEYS: str = ""
    GROQ_API_KEY_1: str = ""
    GROQ_API_KEY_2: str = ""
    GROQ_API_KEY_3: str = ""
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_MAX_OUTPUT_TOKENS: int = 4000
    LLM_TEMPERATURE: float = 0.0

    def get_groq_keys(self) -> List[str]:
        keys: List[str] = []
        if self.GROQ_API_KEYS:
            keys.extend([k.strip() for k in self.GROQ_API_KEYS.split(",") if k.strip()])
        for k in [self.GROQ_API_KEY_1, self.GROQ_API_KEY_2, self.GROQ_API_KEY_3, self.LLM_API_KEY]:
            if k and k.strip() and k.strip() not in keys:
                keys.append(k.strip())
        return keys

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    MEETING_DEDUP_WINDOW_HOURS: int = 6
    MEETING_EXPIRE_HOURS: int = 6
    POLL_INTERVAL_SECONDS: int = 60
    REMINDER_AFTER_HOURS: int = 24
    MAX_REMINDERS: int = 2
    MIN_TRANSCRIPT_WORDS: int = 20
    CONFIDENCE_THRESHOLD: float = 0.5

    @model_validator(mode="after")
    def validate_secrets_in_production(self) -> Settings:
        if self.APP_ENV not in ("test", "dev"):
            required_secrets = [
                ("FIREFLIES_API_KEY", self.FIREFLIES_API_KEY),
                ("FIREFLIES_WEBHOOK_SECRET", self.FIREFLIES_WEBHOOK_SECRET),
                ("LLM_API_KEY", self.LLM_API_KEY),
                ("TELEGRAM_BOT_TOKEN", self.TELEGRAM_BOT_TOKEN),
            ]
            missing = [name for name, val in required_secrets if not val or not val.strip()]
            if missing:
                raise ValueError(f"Missing required secrets for {self.APP_ENV}: {', '.join(missing)}")
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
