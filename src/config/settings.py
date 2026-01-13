"""Application settings using Pydantic."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotionPropertyNames(BaseSettings):
    """Notion database property names mapping."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOTION_PROP_",
        extra="ignore",
    )

    # Property names in your Notion database
    title: str = Field(default="Name")
    status: str = Field(default="Status")
    priority: str = Field(default="Priority")
    due_date: str = Field(default="Due")
    tags: str = Field(default="Tags")
    description: str = Field(default="Description")
    assignee: str = Field(default="Assignee")
    metadata: str = Field(default="Metadata")
    created: str = Field(default="Created")
    # Status property type: "status" or "select"
    status_type: str = Field(default="status")


class NotionPersonalPropertyNames(NotionPropertyNames):
    """Notion personal database property names mapping."""

    model_config = SettingsConfigDict(env_prefix="NOTION_PERSONAL_PROP_", extra="ignore")

    # Property names in your Personal Notion database (override defaults)
    title: str = Field(default="名前")
    status: str = Field(default="ステータス")
    priority: str = Field(default="優先度")
    due_date: str = Field(default="期限")
    tags: str = Field(default="タグ")
    description: str = Field(default="説明")
    assignee: str = Field(default="")
    metadata: str = Field(default="")
    created: str = Field(default="作成日時")
    # Status property type: "status" or "select"
    status_type: str = Field(default="select")


class NotionStatusMapping(BaseSettings):
    """Notion status value mapping."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOTION_STATUS_",
        extra="ignore",
    )

    # Status values in your Notion database
    todo: str = Field(default="Not started")
    in_progress: str = Field(default="In progress")
    done: str = Field(default="Done")
    blocked: str = Field(default="Blocked")


class NotionPriorityMapping(BaseSettings):
    """Notion priority value mapping."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOTION_PRIORITY_",
        extra="ignore",
    )

    # Priority values in your Notion database
    low: str = Field(default="Low")
    medium: str = Field(default="Medium")
    high: str = Field(default="High")
    urgent: str = Field(default="Urgent")


class NotionSettings(BaseSettings):
    """Notion API configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOTION_",
        extra="ignore",
    )

    api_key: Optional[SecretStr] = Field(default=None)
    team_database_id: Optional[str] = Field(default=None)
    personal_database_id: Optional[str] = Field(default=None)
    api_version: str = Field(default="2022-06-28")

    @property
    def properties(self) -> NotionPropertyNames:
        """Get property name mappings for team database."""
        return NotionPropertyNames()

    @property
    def personal_properties(self) -> NotionPersonalPropertyNames:
        """Get property name mappings for personal database."""
        return NotionPersonalPropertyNames()

    @property
    def status_mapping(self) -> NotionStatusMapping:
        """Get status value mappings."""
        return NotionStatusMapping()

    @property
    def priority_mapping(self) -> NotionPriorityMapping:
        """Get priority value mappings."""
        return NotionPriorityMapping()


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
    task_sync_cron: str = Field(default="0 */1 * * *")  # Every hour


class TaskSyncSettings(BaseSettings):
    """Task sync configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TASK_SYNC_",
        extra="ignore",
    )

    enabled: bool = Field(default=True)
    # Comma-separated list of assignee names to sync
    assignees: str = Field(default="")
    # Comma-separated list of tags to sync
    tags: str = Field(default="")
    # Whether to sync task updates
    sync_updates: bool = Field(default=True)
    # Whether to skip completed tasks
    skip_done: bool = Field(default=True)

    def get_assignees(self) -> list[str]:
        """Get list of assignees to sync."""
        if not self.assignees:
            return []
        return [a.strip() for a in self.assignees.split(",") if a.strip()]

    def get_tags(self) -> list[str]:
        """Get list of tags to sync."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


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

    @property
    def task_sync(self) -> TaskSyncSettings:
        return TaskSyncSettings()


@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for testing)."""
    get_settings.cache_clear()
