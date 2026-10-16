"""
Unit tests for webhook security and signature verification.
"""
import hashlib
import hmac
from app.services.webhook_security import verify_signature


def test_valid_signature_sha256_prefix():
    secret = "my_webhook_secret"
    body = b'{"meetingId":"123","eventType":"Transcription completed"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(body, f"sha256={sig}", secret) is True
    assert verify_signature(body, sig, secret) is True


def test_invalid_signature():
    secret = "my_webhook_secret"
    body = b'{"meetingId":"123"}'
    assert verify_signature(body, "sha256=invalidhex", secret) is False


def test_tampered_body():
    secret = "my_webhook_secret"
    body = b'{"meetingId":"123"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    tampered = b'{"meetingId":"124"}'
    assert verify_signature(tampered, sig, secret) is False


def test_missing_header_or_secret():
    body = b'{"meetingId":"123"}'
    assert verify_signature(body, None, "secret") is False
    assert verify_signature(body, "sig", "") is False
