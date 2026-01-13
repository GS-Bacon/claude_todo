"""Application settings using Pydantic."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotionSettings(BaseSettings):
    """Notion API configuration."""

    model_config = SettingsConfigDict(env_prefix="NOTION_", extra="ignore")

    api_key: Optional[SecretStr] = Field(default=None)
    team_database_id: Optional[str] = Field(default=None)
    personal_database_id: Optional[str] = Field(default=None)


class DiscordSettings(BaseSettings):
    """Discord webhook configuration."""

    model_config = SettingsConfigDict(env_prefix="DISCORD_", extra="ignore")

    webhook_url: Optional[SecretStr] = Field(default=None)
    username: str = Field(default="TaskBot")


class SlackSettings(BaseSettings):
    """Slack configuration."""

    model_config = SettingsConfigDict(env_prefix="SLACK_", extra="ignore")

    signing_secret: Optional[SecretStr] = Field(default=None)
    bot_token: Optional[SecretStr] = Field(default=None)


class PrintWebhookSettings(BaseSettings):
    """Print webhook configuration."""

    model_config = SettingsConfigDict(env_prefix="PRINT_WEBHOOK_", extra="ignore")

    url: Optional[str] = Field(default=None)
    api_key: Optional[SecretStr] = Field(default=None)


class SchedulerSettings(BaseSettings):
    """Scheduler configuration."""

    model_config = SettingsConfigDict(env_prefix="SCHEDULER_", extra="ignore")

    enabled: bool = Field(default=True)
    timezone: str = Field(default="Asia/Tokyo")
    sync_cron: str = Field(default="*/15 * * * *")
    notification_cron: str = Field(default="0 9 * * *")


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Nested settings - manually create to avoid env prefix issues
    @property
    def notion(self) -> NotionSettings:
        return NotionSettings()

    @property
    def discord(self) -> DiscordSettings:
        return DiscordSettings()

    @property
    def slack(self) -> SlackSettings:
        return SlackSettings()

    @property
    def print_webhook(self) -> PrintWebhookSettings:
        return PrintWebhookSettings()

    @property
    def scheduler(self) -> SchedulerSettings:
        return SchedulerSettings()


@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for testing)."""
    get_settings.cache_clear()
