"""Tests for MentionService and parsers."""

import pytest
from datetime import datetime

from src.services.mention_service import MentionService
from src.parsers.slack_parser import SlackWebhookParser
from src.parsers.discord_parser import DiscordWebhookParser
from src.repositories.memory import InMemoryTaskRepository
from src.domain.models import Mention, TaskPriority, TaskStatus, TaskSource


class TestSlackWebhookParser:
    """Tests for SlackWebhookParser."""

    @pytest.fixture
    def parser(self) -> SlackWebhookParser:
        return SlackWebhookParser()

    def test_platform_name(self, parser):
        """Should return 'slack' as platform name."""
        assert parser.platform == "slack"

    def test_can_parse_app_mention(self, parser):
        """Should recognize Slack app_mention events."""
        payload = {
            "type": "event_callback",
            "event": {"type": "app_mention", "text": "test"},
        }
        assert parser.can_parse(payload) is True

    def test_can_parse_message(self, parser):
        """Should recognize Slack message events."""
        payload = {
            "type": "event_callback",
            "event": {"type": "message", "text": "test"},
        }
        assert parser.can_parse(payload) is True

    def test_cannot_parse_discord(self, parser):
        """Should not recognize Discord payloads."""
        payload = {"type": 1, "guild_id": "123"}
        assert parser.can_parse(payload) is False

    def test_cannot_parse_url_verification(self, parser):
        """Should not parse URL verification requests as mentions."""
        payload = {"type": "url_verification", "challenge": "test"}
        assert parser.can_parse(payload) is False

    def test_parse_extracts_fields(self, parser):
        """Should extract fields from Slack payload."""
        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "app_mention",
                "channel": "C456",
                "channel_name": "general",
                "user": "U789",
                "user_name": "john",
                "text": "Please review this PR",
                "ts": "1704067200.000000",
            },
        }
        mention = parser.parse(payload)

        assert mention.source_platform == "slack"
        assert mention.channel_id == "C456"
        assert mention.user_id == "U789"
        assert mention.message_text == "Please review this PR"
        assert "slack.com" in mention.message_url

    def test_parse_handles_missing_timestamp(self, parser):
        """Should handle missing timestamp gracefully."""
        payload = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "channel": "C456",
                "text": "Test",
            },
        }
        mention = parser.parse(payload)
        assert mention.timestamp is not None


class TestDiscordWebhookParser:
    """Tests for DiscordWebhookParser."""

    @pytest.fixture
    def parser(self) -> DiscordWebhookParser:
        return DiscordWebhookParser()

    def test_platform_name(self, parser):
        """Should return 'discord' as platform name."""
        assert parser.platform == "discord"

    def test_can_parse_with_guild_id(self, parser):
        """Should recognize Discord payloads with guild_id."""
        payload = {"type": 0, "guild_id": "123", "channel_id": "456"}
        assert parser.can_parse(payload) is True

    def test_can_parse_with_channel_id(self, parser):
        """Should recognize Discord payloads with channel_id."""
        payload = {"type": 0, "channel_id": "456"}
        assert parser.can_parse(payload) is True

    def test_cannot_parse_slack(self, parser):
        """Should not recognize Slack payloads."""
        payload = {"type": "event_callback", "event": {"type": "message"}}
        assert parser.can_parse(payload) is False

    def test_parse_extracts_fields(self, parser):
        """Should extract fields from Discord payload."""
        payload = {
            "type": 0,
            "id": "msg123",
            "guild_id": "guild456",
            "channel_id": "channel789",
            "channel": {"name": "general"},
            "content": "Deploy to staging !urgent",
            "author": {"id": "user123", "username": "dev_user"},
            "timestamp": "2024-01-01T12:00:00Z",
        }
        mention = parser.parse(payload)

        assert mention.source_platform == "discord"
        assert mention.channel_id == "channel789"
        assert mention.channel_name == "general"
        assert mention.user_id == "user123"
        assert mention.user_name == "dev_user"
        assert mention.message_text == "Deploy to staging !urgent"
        assert "discord.com" in mention.message_url

    def test_parse_handles_missing_fields(self, parser):
        """Should handle missing optional fields."""
        payload = {
            "type": 0,
            "channel_id": "456",
            "content": "Test message",
        }
        mention = parser.parse(payload)

        assert mention.source_platform == "discord"
        assert mention.channel_id == "456"
        assert mention.user_id == ""
        assert mention.message_text == "Test message"


class TestMentionService:
    """Tests for MentionService."""

    @pytest.fixture
    def repository(self) -> InMemoryTaskRepository:
        return InMemoryTaskRepository()

    @pytest.fixture
    def parsers(self) -> list:
        return [SlackWebhookParser(), DiscordWebhookParser()]

    @pytest.fixture
    def service(self, repository, parsers) -> MentionService:
        return MentionService(repository, parsers)

    def test_get_parser_for_slack(self, service):
        """Should return Slack parser for Slack payloads."""
        payload = {
            "type": "event_callback",
            "event": {"type": "app_mention", "text": "test"},
        }
        parser = service.get_parser(payload)
        assert parser is not None
        assert parser.platform == "slack"

    def test_get_parser_for_discord(self, service):
        """Should return Discord parser for Discord payloads."""
        payload = {"type": 0, "guild_id": "123", "channel_id": "456"}
        parser = service.get_parser(payload)
        assert parser is not None
        assert parser.platform == "discord"

    def test_get_parser_returns_none_for_unknown(self, service):
        """Should return None for unknown payloads."""
        payload = {"unknown": "format"}
        parser = service.get_parser(payload)
        assert parser is None

    def test_extract_priority_high(self, service):
        """Should extract high priority from text."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Fix the bug !high",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["priority"] == TaskPriority.HIGH

    def test_extract_priority_urgent(self, service):
        """Should extract urgent priority from text."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="ASAP !urgent task",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["priority"] == TaskPriority.URGENT

    def test_extract_priority_default(self, service):
        """Should default to medium priority."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Regular task",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["priority"] == TaskPriority.MEDIUM

    def test_extract_due_date(self, service):
        """Should extract due date from text."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Complete report due:2024-01-15",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["due_date"] == datetime(2024, 1, 15)

    def test_extract_due_date_none_when_missing(self, service):
        """Should return None when no due date."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="No due date",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["due_date"] is None

    def test_extract_tags(self, service):
        """Should extract tags from text."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Fix login #bug #auth #urgent",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["tags"] == ["bug", "auth", "urgent"]

    def test_extract_clean_title(self, service):
        """Should clean metadata from title."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="<@U123> Review PR !high due:2024-01-15 #review",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["title"] == "Review PR"

    def test_extract_default_title(self, service):
        """Should use default title when text is just metadata."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="<@U123> !high #task",
            timestamp=datetime.now(),
        )
        details = service.extract_task_details(mention)
        assert details["title"] == "Task from mention"

    @pytest.mark.asyncio
    async def test_process_mention_creates_task(self, service, repository):
        """Should create task from mention."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Review PR #review !high",
            timestamp=datetime.now(),
            message_url="https://slack.com/...",
        )
        task = await service.process_mention(mention)

        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.HIGH
        assert task.source == TaskSource.SLACK_MENTION
        assert "review" in task.tags
        assert await repository.exists(task.id)

    @pytest.mark.asyncio
    async def test_process_mention_stores_metadata(self, service, repository):
        """Should store mention metadata in task."""
        mention = Mention(
            source_platform="discord",
            channel_id="C123",
            channel_name="dev-chat",
            user_id="U456",
            user_name="jane",
            message_text="Fix bug",
            timestamp=datetime.now(),
            message_url="https://discord.com/...",
        )
        task = await service.process_mention(mention)

        assert task.metadata["source_platform"] == "discord"
        assert task.metadata["source_channel"] == "C123"
        assert task.metadata["source_user_name"] == "jane"
        assert task.metadata["message_url"] == "https://discord.com/..."

    @pytest.mark.asyncio
    async def test_process_webhook_slack(self, service, repository):
        """Should process Slack webhook end-to-end."""
        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "app_mention",
                "channel": "C456",
                "user": "U789",
                "user_name": "dev",
                "text": "Deploy to prod !urgent",
                "ts": "1704067200.000000",
            },
        }
        task = await service.process_webhook(payload)

        assert task is not None
        assert task.priority == TaskPriority.URGENT
        assert task.source == TaskSource.SLACK_MENTION

    @pytest.mark.asyncio
    async def test_process_webhook_discord(self, service, repository):
        """Should process Discord webhook end-to-end."""
        payload = {
            "type": 0,
            "id": "msg123",
            "guild_id": "guild456",
            "channel_id": "channel789",
            "content": "Code review needed #review",
            "author": {"id": "user123", "username": "reviewer"},
            "timestamp": "2024-01-01T12:00:00Z",
        }
        task = await service.process_webhook(payload)

        assert task is not None
        assert task.source == TaskSource.DISCORD_MENTION
        assert "review" in task.tags

    @pytest.mark.asyncio
    async def test_process_webhook_unknown_returns_none(self, service):
        """Should return None for unknown webhook formats."""
        payload = {"unknown": "format"}
        task = await service.process_webhook(payload)
        assert task is None
