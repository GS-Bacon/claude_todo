"""Tests for configuration settings."""

import os
import pytest
from unittest.mock import patch

from src.config.settings import (
    AppSettings,
    NotionSettings,
    DiscordSettings,
    SlackSettings,
    PrintWebhookSettings,
    SchedulerSettings,
    get_settings,
    clear_settings_cache,
)


class TestNotionSettings:
    """Tests for NotionSettings."""

    def test_loads_from_env(self):
        """Should load settings from environment variables."""
        env_vars = {
            "NOTION_API_KEY": "secret_test_key",
            "NOTION_TEAM_DATABASE_ID": "team-db-123",
            "NOTION_PERSONAL_DATABASE_ID": "personal-db-456",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = NotionSettings()
            assert settings.api_key.get_secret_value() == "secret_test_key"
            assert settings.team_database_id == "team-db-123"
            assert settings.personal_database_id == "personal-db-456"

    def test_defaults_to_none(self):
        """Should default to None when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing NOTION_ vars
            for key in list(os.environ.keys()):
                if key.startswith("NOTION_"):
                    del os.environ[key]

            settings = NotionSettings()
            assert settings.api_key is None
            assert settings.team_database_id is None


class TestDiscordSettings:
    """Tests for DiscordSettings."""

    def test_loads_webhook_url(self):
        """Should load webhook URL from environment."""
        env_vars = {"DISCORD_WEBHOOK_URL": "https://discord.com/webhook/test"}
        with patch.dict(os.environ, env_vars, clear=False):
            settings = DiscordSettings()
            assert (
                settings.webhook_url.get_secret_value()
                == "https://discord.com/webhook/test"
            )

    def test_default_username(self):
        """Should have default username."""
        settings = DiscordSettings()
        assert settings.username == "TaskBot"


class TestSlackSettings:
    """Tests for SlackSettings."""

    def test_loads_from_env(self):
        """Should load Slack settings from environment."""
        env_vars = {
            "SLACK_SIGNING_SECRET": "slack_secret_123",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = SlackSettings()
            assert settings.signing_secret.get_secret_value() == "slack_secret_123"
            assert settings.bot_token.get_secret_value() == "xoxb-test-token"


class TestPrintWebhookSettings:
    """Tests for PrintWebhookSettings."""

    def test_loads_from_env(self):
        """Should load print webhook settings from environment."""
        env_vars = {
            "PRINT_WEBHOOK_URL": "http://print.local/webhook",
            "PRINT_WEBHOOK_API_KEY": "print_api_key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = PrintWebhookSettings()
            assert settings.url == "http://print.local/webhook"
            assert settings.api_key.get_secret_value() == "print_api_key"


class TestSchedulerSettings:
    """Tests for SchedulerSettings."""

    def test_default_values(self):
        """Should have sensible defaults."""
        settings = SchedulerSettings()
        assert settings.enabled is True
        assert settings.timezone == "Asia/Tokyo"
        assert settings.sync_cron == "*/15 * * * *"
        assert settings.notification_cron == "0 9 * * *"

    def test_custom_values(self):
        """Should accept custom values from environment."""
        env_vars = {
            "SCHEDULER_ENABLED": "false",
            "SCHEDULER_TIMEZONE": "UTC",
            "SCHEDULER_SYNC_CRON": "0 * * * *",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = SchedulerSettings()
            assert settings.enabled is False
            assert settings.timezone == "UTC"
            assert settings.sync_cron == "0 * * * *"


class TestAppSettings:
    """Tests for AppSettings."""

    def test_default_values(self):
        """Should have sensible defaults."""
        settings = AppSettings()
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000

    def test_nested_settings(self):
        """Should have nested settings accessible."""
        settings = AppSettings()
        assert isinstance(settings.notion, NotionSettings)
        assert isinstance(settings.discord, DiscordSettings)
        assert isinstance(settings.slack, SlackSettings)
        assert isinstance(settings.print_webhook, PrintWebhookSettings)
        assert isinstance(settings.scheduler, SchedulerSettings)

    def test_custom_host_port(self):
        """Should accept custom host and port from environment."""
        env_vars = {
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "DEBUG": "true",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = AppSettings()
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.debug is True


class TestGetSettings:
    """Tests for get_settings function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_settings_cache()

    def test_returns_app_settings(self):
        """Should return AppSettings instance."""
        settings = get_settings()
        assert isinstance(settings, AppSettings)

    def test_caches_result(self):
        """Should return cached instance on subsequent calls."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_clear_cache(self):
        """Should allow clearing the cache."""
        settings1 = get_settings()
        clear_settings_cache()
        settings2 = get_settings()
        # After clearing cache, should be a new instance
        # (though with same values if env hasn't changed)
        assert isinstance(settings2, AppSettings)
