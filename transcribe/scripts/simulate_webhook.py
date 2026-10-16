"""
Simulates sending a signed Fireflies webhook payload to a running local server.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import httpx


def main():
    parser = argparse.ArgumentParser(description="Simulate signed Fireflies webhook")
    parser.add_argument("--meeting-id", default="ff_sim_123", help="Fireflies meeting ID")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/transcribe/webhooks/fireflies", help="Webhook endpoint")
    parser.add_argument("--secret", default="dummy_webhook_secret", help="Webhook secret")
    args = parser.parse_args()

    payload = {
        "meetingId": args.meeting_id,
        "eventType": "Transcription completed",
        "clientReferenceId": None,
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(args.secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "x-hub-signature": f"sha256={sig}",
    }

    print(f"Sending signed webhook to {args.url} (meetingId={args.meeting_id})...")
    resp = httpx.post(args.url, content=raw_body, headers=headers)
    print(f"Response status: {resp.status_code}")
    print(f"Response text: {resp.text}")


if __name__ == "__main__":
    main()
