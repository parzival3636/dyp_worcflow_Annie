"""
Integration tests for FirefliesProvider using httpx.MockTransport (PRD Section 15.3, F1-F10).
No real network calls.
"""
import asyncio
import json
import pytest
import httpx
from app.providers.fireflies import FirefliesProvider, ProviderError


def test_f1_dispatch_success():
    async def _test():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"addToLiveMeeting": {"success": True}}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FirefliesProvider(api_key="secret_key_123", client=client)
            res = await provider.dispatch_bot("https://meet.google.com/abc-defg-hij", "ref_1")
            assert res.success is True

    asyncio.run(_test())


def test_f2_graphql_errors_raised():
    async def _test():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"errors": [{"message": "Meeting not found"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FirefliesProvider(api_key="secret_key_123", client=client)
            with pytest.raises(ProviderError, match="Meeting not found"):
                await provider.dispatch_bot("https://meet.google.com/abc-defg-hij", "ref_1")

    asyncio.run(_test())


def test_f4_http_401_auth_error():
    async def _test():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "Unauthorized"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FirefliesProvider(api_key="secret_key_123", client=client)
            with pytest.raises(ProviderError) as exc_info:
                await provider.dispatch_bot("https://meet.google.com/abc-defg-hij", "ref_1")
            assert exc_info.value.code == "AUTH"

    asyncio.run(_test())


def test_f5_rate_limit_error():
    async def _test():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "Too Many Requests"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FirefliesProvider(api_key="secret_key_123", client=client)
            with pytest.raises(ProviderError) as exc_info:
                await provider.dispatch_bot("https://meet.google.com/abc-defg-hij", "ref_1")
            assert exc_info.value.code == "RATE_LIMIT"
            assert exc_info.value.retryable is True

    asyncio.run(_test())


def test_f6_fetch_transcript_success():
    async def _test():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "data": {
                    "transcript": {
                        "id": "t1",
                        "title": "Sync",
                        "sentences": [
                            {"index": 0, "speaker_name": "Alice", "text": "Hello", "start_time": 0.0, "end_time": 1.0}
                        ]
                    }
                }
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FirefliesProvider(api_key="secret_key_123", client=client)
            t = await provider.fetch_transcript("t1")
            assert t is not None
            assert t.id == "t1"
            assert len(t.sentences) == 1

    asyncio.run(_test())


def test_f7_f8_fetch_transcript_null_or_empty():
    async def _test():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"transcript": {"id": "t2", "sentences": []}}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FirefliesProvider(api_key="secret_key_123", client=client)
            t = await provider.fetch_transcript("t2")
            assert t is None  # Not ready

    asyncio.run(_test())
