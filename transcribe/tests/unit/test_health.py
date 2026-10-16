"""
Tests for health check endpoint.
"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/api/v1/transcribe/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
