import json
import os
import httpx
import pytest

from backend.config import settings
from backend.llm import (
    call_json,
    P1Project,
    P3Reply,
    P4Verdict,
    P5Contradiction,
    P6Route,
)


def make_chat_response(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def test_l1_valid_json():
    called = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called += 1
        content = json.dumps({"name": "Pilot Engine", "summary": "Project coordinator", "duration_hours": 24})
        return httpx.Response(200, json=make_chat_response(content))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_json("System prompt", "User prompt", P1Project, retries=2, http_client=client)

    assert called == 1
    assert isinstance(result, P1Project)
    assert result.name == "Pilot Engine"
    assert result.duration_hours == 24


def test_l2_json_wrapped_in_code_fences():
    def handler(request: httpx.Request) -> httpx.Response:
        content = "```json\n{\"name\": \"Fenced App\", \"summary\": \"With fences\", \"duration_hours\": 20}\n```"
        return httpx.Response(200, json=make_chat_response(content))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_json("System", "User", P1Project, retries=2, http_client=client)

    assert isinstance(result, P1Project)
    assert result.name == "Fenced App"


def test_l3_json_with_prose_before_and_after():
    def handler(request: httpx.Request) -> httpx.Response:
        content = (
            "Sure! Here is the JSON you requested:\n"
            "{\"name\": \"Prose App\", \"summary\": \"Embedded in prose\", \"duration_hours\": 15}\n"
            "Let me know if you need any adjustments!"
        )
        return httpx.Response(200, json=make_chat_response(content))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_json("System", "User", P1Project, retries=2, http_client=client)

    assert isinstance(result, P1Project)
    assert result.name == "Prose App"
    assert result.duration_hours == 15


def test_l4_invalid_then_valid_on_retry():
    calls = 0
    prompts_received = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        data = json.loads(request.content)
        prompts_received.append(data["messages"][1]["content"])

        if calls == 1:
            # Missing required field 'summary'
            bad_content = json.dumps({"name": "Incomplete"})
            return httpx.Response(200, json=make_chat_response(bad_content))
        else:
            good_content = json.dumps({"name": "Fixed Project", "summary": "Has summary now", "duration_hours": 20})
            return httpx.Response(200, json=make_chat_response(good_content))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_json("System", "Initial User Prompt", P1Project, retries=2, http_client=client)

    assert calls == 2
    assert isinstance(result, P1Project)
    assert result.name == "Fixed Project"
    # Ensure validation error was appended in retry prompt
    assert "Validation error" in prompts_received[1]


def test_l5_invalid_three_times_returns_fallback_without_exception():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=make_chat_response("Not valid JSON at all"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    # For P3Reply, fallback should have intent='unclear' and needs_clarification=True
    result = call_json("System", "Working on stuff", P3Reply, retries=2, http_client=client)

    assert calls == 3  # 1 initial + 2 retries
    assert isinstance(result, P3Reply)
    assert result.intent == "unclear"
    assert result.needs_clarification is True
    assert result.confidence == 0.0


def test_l6_timeout_or_network_error_returns_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out after 30s")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = call_json("System", "Some input", P4Verdict, retries=1, http_client=client)

    assert isinstance(result, P4Verdict)
    assert result.verdict == "no_evidence"
    assert result.confidence == 0.0
    assert result.reason == "Verifier unavailable"


def test_l7_every_attempt_logged_without_secrets():
    log_path = os.path.join("docs", "demo-evidence", "llm.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    secret_key = "gsk_secret_token_12345"
    old_key = settings.LLM_API_KEY
    settings.LLM_API_KEY = secret_key

    try:
        def handler(request: httpx.Request) -> httpx.Response:
            content = json.dumps({"has_contradiction": False})
            return httpx.Response(200, json=make_chat_response(content))

        client = httpx.Client(transport=httpx.MockTransport(handler))
        call_json("System prompt", "User prompt", P5Contradiction, retries=1, http_client=client)

        assert os.path.exists(log_path)
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) >= 1
        last_log = json.loads(lines[-1])
        assert last_log["model"] == settings.LLM_MODEL
        assert "parsed" in last_log

        # Ensure no secret key appears anywhere in the log
        with open(log_path, "r", encoding="utf-8") as f:
            all_text = f.read()
        assert secret_key not in all_text

    finally:
        settings.LLM_API_KEY = old_key


def test_l8_request_temperature_is_0_point_1():
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        content = json.dumps({"member_id": 2, "reason": "Expert in Docker"})
        return httpx.Response(200, json=make_chat_response(content))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_json("System", "Who should fix docker?", P6Route, retries=1, http_client=client)

    assert "temperature" in captured_payload
    assert captured_payload["temperature"] == 0.1
