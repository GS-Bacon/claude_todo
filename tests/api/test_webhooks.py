"""Tests for webhook endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.container import get_container, reset_container
from src.repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository


@pytest.fixture(autouse=True)
def setup_container():
    """Set up container with in-memory repositories for testing."""
    reset_container()
    container = get_container()
    container.configure_task_repository(InMemoryTaskRepository)
    container.configure_personal_task_repository(InMemoryTaskRepository)
    container.configure_cache_repository(InMemoryCacheRepository)
    yield
    reset_container()


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestSlackWebhook:
    """Tests for Slack webhook endpoint."""

    def test_url_verification(self, client):
        """Should return challenge for URL verification."""
        payload = {
            "type": "url_verification",
            "challenge": "test-challenge-123",
        }

        response = client.post("/webhooks/slack", json=payload)

        assert response.status_code == 200
        assert response.json()["challenge"] == "test-challenge-123"

    def test_event_callback_creates_task(self, client):
        """Should create task from app_mention event."""
        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "app_mention",
                "channel": "C456",
                "user": "U789",
                "text": "Review the PR !high",
                "ts": "1704067200.000000",
            },
        }

        response = client.post("/webhooks/slack", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "task_id" in data

    def test_message_event_creates_task(self, client):
        """Should create task from message event."""
        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "message",
                "channel": "C456",
                "user": "U789",
                "text": "Deploy to staging #deploy",
                "ts": "1704067200.000000",
            },
        }

        response = client.post("/webhooks/slack", json=payload)

        assert response.status_code == 200

    def test_unknown_event_returns_ok(self, client):
        """Should return ok for unknown events."""
        payload = {
            "type": "unknown_event",
        }

        response = client.post("/webhooks/slack", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestDiscordWebhook:
    """Tests for Discord webhook endpoint."""

    def test_ping_verification(self, client):
        """Should return type 1 for ping verification."""
        payload = {"type": 1}

        response = client.post("/webhooks/discord", json=payload)

        assert response.status_code == 200
        assert response.json()["type"] == 1

    def test_message_creates_task(self, client):
        """Should create task from message event."""
        payload = {
            "type": 0,
            "id": "msg123",
            "guild_id": "guild456",
            "channel_id": "channel789",
            "content": "Fix the bug !urgent #bug",
            "author": {"id": "user123", "username": "dev_user"},
            "timestamp": "2024-01-01T12:00:00Z",
        }

        response = client.post("/webhooks/discord", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "task_id" in data

    def test_unknown_type_returns_ok(self, client):
        """Should return ok for unknown message types."""
        payload = {
            "type": 99,
            "channel_id": "456",
        }

        response = client.post("/webhooks/discord", json=payload)

        assert response.status_code == 200


class TestWebhookHealth:
    """Tests for webhook health endpoint."""

    def test_health_check(self, client):
        """Should return healthy status."""
        response = client.get("/webhooks/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
