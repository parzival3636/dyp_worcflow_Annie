"""
Webhook security and idempotency utilities.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.orm import WebhookEvent

logger = logging.getLogger("transcribe.security")


def verify_signature(raw_body: bytes, header_value: Optional[str], secret: str) -> bool:
    """
    Verifies HMAC-SHA256 signature using constant-time comparison.
    Accepts both 'sha256=<hex>' and bare hex strings.
    """
    if not header_value or not secret or not raw_body:
        return False

    header_clean = header_value.strip()
    if header_clean.startswith("sha256="):
        signature_to_check = header_clean[7:].strip()
    else:
        signature_to_check = header_clean

    computed = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed.lower(), signature_to_check.lower())


def record_event_once(session: Session, provider: str, meeting_id: str, event_type: str) -> bool:
    """
    Inserts a webhook event into the database with unique constraint checking.
    Returns True if the event is new, False if it was already processed (duplicate).
    """
    evt = WebhookEvent(
        provider=provider,
        provider_meeting_id=meeting_id,
        event_type=event_type,
        received_at=datetime.now(timezone.utc),
    )
    session.add(evt)
    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False
