"""
Structured logging configuration with secret redaction filter.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from app.config import get_settings

_BEARER_PATTERN = re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE)


class RedactingFilter(logging.Filter):
    """Filter that redacts secrets and bearer tokens from log messages."""

    def __init__(self, secrets: list[str] | None = None):
        super().__init__()
        self.secrets = [s for s in (secrets or []) if s and len(s) > 3]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(v) if isinstance(v, str) else v for v in record.args)
        return True

    def _redact(self, text: str) -> str:
        # Redact bearer tokens
        text = _BEARER_PATTERN.sub(r"Bearer [REDACTED]", text)
        # Redact configured secrets
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED]")
        return text


class JsonFormatter(logging.Formatter):
    """Simple JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging():
    settings = get_settings()
    secrets = [
        settings.FIREFLIES_API_KEY,
        settings.FIREFLIES_WEBHOOK_SECRET,
        settings.LLM_API_KEY,
        settings.TELEGRAM_BOT_TOKEN,
        settings.TELEGRAM_WEBHOOK_SECRET,
    ]
    redacting_filter = RedactingFilter(secrets=secrets)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(redacting_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Avoid duplicate handlers
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]
