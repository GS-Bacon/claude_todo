"""Tests for NotificationService and notification senders."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import httpx

from src.services.notification_service import NotificationService
from src.notifications.discord_sender import DiscordNotificationSender
from src.notifications.print_webhook_sender import PrintWebhookSender
from src.repositories.memory import InMemoryCacheRepository
from src.domain.models import (
    Notification,
    Task,
    TaskId,
    TaskStatus,
    TaskSource,
    TaskPriority,
)


class TestDiscordNotificationSender:
    """Tests for DiscordNotificationSender."""

    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def sender(self, mock_client) -> DiscordNotificationSender:
        """Create sender with mock client."""
        return DiscordNotificationSender(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            http_client=mock_client,
        )

    def test_channel_name(self, sender):
        """Should return 'discord' as channel name."""
        assert sender.channel_name == "discord"

    @pytest.mark.asyncio
    async def test_send_success(self, sender, mock_client):
        """Should return True on successful send."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.post.return_value = mock_response

        notification = Notification(
            title="Test Notification",
            message="Test message",
            created_at=datetime.now(),
        )

        result = await sender.send(notification)

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_failure(self, sender, mock_client):
        """Should return False on HTTP error."""
        mock_client.post.side_effect = httpx.HTTPError("Connection failed")

        notification = Notification(
            title="Test",
            message="Test",
            created_at=datetime.now(),
        )

        result = await sender.send(notification)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_with_priority(self, sender, mock_client):
        """Should include priority in embed."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.post.return_value = mock_response

        notification = Notification(
            title="Urgent Task",
            message="This is urgent",
            priority=TaskPriority.URGENT,
            created_at=datetime.now(),
        )

        await sender.send(notification)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        fields = payload["embeds"][0]["fields"]

        priority_field = next(f for f in fields if f["name"] == "Priority")
        assert priority_field["value"] == "Urgent"

    @pytest.mark.asyncio
    async def test_send_with_due_date(self, sender, mock_client):
        """Should include due date in embed."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.post.return_value = mock_response

        due_date = datetime(2024, 1, 15, 14, 30)
        notification = Notification(
            title="Task",
            message="Message",
            due_date=due_date,
            created_at=datetime.now(),
        )

        await sender.send(notification)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        fields = payload["embeds"][0]["fields"]

        due_field = next(f for f in fields if f["name"] == "Due Date")
        assert "2024-01-15" in due_field["value"]

    def test_color_for_priority(self, sender):
        """Should return correct colors for priorities."""
        assert sender._get_color_for_priority(TaskPriority.LOW) == 0x2ECC71
        assert sender._get_color_for_priority(TaskPriority.MEDIUM) == 0x3498DB
        assert sender._get_color_for_priority(TaskPriority.HIGH) == 0xF39C12
        assert sender._get_color_for_priority(TaskPriority.URGENT) == 0xE74C3C
        assert sender._get_color_for_priority(None) == 0x808080


class TestPrintWebhookSender:
    """Tests for PrintWebhookSender."""

    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def sender(self, mock_client) -> PrintWebhookSender:
        """Create sender with mock client."""
        return PrintWebhookSender(
            webhook_url="https://print.local/webhook",
            api_key="test-api-key",
            http_client=mock_client,
        )

    def test_channel_name(self, sender):
        """Should return 'print' as channel name."""
        assert sender.channel_name == "print"

    @pytest.mark.asyncio
    async def test_send_success(self, sender, mock_client):
        """Should return True on successful send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        notification = Notification(
            title="Print Task",
            message="Print this message",
            created_at=datetime.now(),
        )

        result = await sender.send(notification)

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_includes_api_key(self, sender, mock_client):
        """Should include API key in headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        notification = Notification(
            title="Test",
            message="Test",
            created_at=datetime.now(),
        )

        await sender.send(notification)

        call_args = mock_client.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["X-API-Key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_send_failure(self, sender, mock_client):
        """Should return False on HTTP error."""
        mock_client.post.side_effect = httpx.HTTPError("Connection failed")

        notification = Notification(
            title="Test",
            message="Test",
            created_at=datetime.now(),
        )

        result = await sender.send(notification)

        assert result is False

    @pytest.mark.asyncio
    async def test_payload_includes_formatted_text(self, sender, mock_client):
        """Should include formatted text for printing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        notification = Notification(
            title="Important Task",
            message="Do this thing",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
        )

        await sender.send(notification)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]

        assert "formatted_text" in payload
        assert "Important Task" in payload["formatted_text"]

    def test_format_for_print(self, sender):
        """Should format notification properly for printing."""
        notification = Notification(
            title="Test Title",
            message="Test Message",
            priority=TaskPriority.HIGH,
            due_date=datetime(2024, 1, 15, 10, 0),
            source_info="slack - john",
            created_at=datetime(2024, 1, 14, 9, 0, 0),
        )

        formatted = sender._format_for_print(notification)

        assert "Test Title" in formatted
        assert "Test Message" in formatted
        assert "HIGH" in formatted
        assert "2024-01-15" in formatted
        assert "slack - john" in formatted


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def cache(self) -> InMemoryCacheRepository:
        return InMemoryCacheRepository()

    @pytest.fixture
    def mock_discord_sender(self):
        """Create mock Discord sender."""
        sender = AsyncMock()
        sender.channel_name = "discord"
        sender.send = AsyncMock(return_value=True)
        return sender

    @pytest.fixture
    def mock_print_sender(self):
        """Create mock print sender."""
        sender = AsyncMock()
        sender.channel_name = "print"
        sender.send = AsyncMock(return_value=True)
        return sender

    @pytest.fixture
    def service(self, cache, mock_discord_sender, mock_print_sender) -> NotificationService:
        """Create service with mock senders."""
        return NotificationService(
            cache_repository=cache,
            senders=[mock_discord_sender, mock_print_sender],
        )

    def test_senders_property(self, service, mock_discord_sender, mock_print_sender):
        """Should return list of senders."""
        assert len(service.senders) == 2
        assert mock_discord_sender in service.senders
        assert mock_print_sender in service.senders

    def test_add_sender(self, cache):
        """Should add sender to list."""
        service = NotificationService(cache, [])
        mock_sender = AsyncMock()
        mock_sender.channel_name = "new"

        service.add_sender(mock_sender)

        assert len(service.senders) == 1
        assert mock_sender in service.senders

    def test_remove_sender(self, service):
        """Should remove sender by channel name."""
        result = service.remove_sender("discord")

        assert result is True
        assert len(service.senders) == 1
        assert all(s.channel_name != "discord" for s in service.senders)

    def test_remove_sender_not_found(self, service):
        """Should return False when sender not found."""
        result = service.remove_sender("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_all_channels(
        self, service, mock_discord_sender, mock_print_sender
    ):
        """Should send to all channels when none specified."""
        notification = Notification(
            title="Test",
            message="Test",
            created_at=datetime.now(),
        )

        results = await service.send_notification(notification)

        assert results["discord"] is True
        assert results["print"] is True
        mock_discord_sender.send.assert_called_once()
        mock_print_sender.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_specific_channels(
        self, service, mock_discord_sender, mock_print_sender
    ):
        """Should send only to specified channels."""
        notification = Notification(
            title="Test",
            message="Test",
            created_at=datetime.now(),
        )

        results = await service.send_notification(notification, channels=["discord"])

        assert "discord" in results
        assert "print" not in results
        mock_discord_sender.send.assert_called_once()
        mock_print_sender.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_task_reminder(self, service, mock_discord_sender):
        """Should send reminder notification for task."""
        task = Task(
            id=TaskId.generate(),
            title="Review PR",
            description="Review the pull request",
            status=TaskStatus.TODO,
            source=TaskSource.SLACK_MENTION,
            priority=TaskPriority.HIGH,
            due_date=datetime.now() + timedelta(hours=2),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        results = await service.send_task_reminder(task)

        assert results["discord"] is True
        call_args = mock_discord_sender.send.call_args
        notification = call_args[0][0]
        assert "Review PR" in notification.title
        assert notification.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_send_due_notifications(
        self, service, cache, mock_discord_sender
    ):
        """Should send notifications for tasks due today."""
        today = datetime.now()
        due_today = Task(
            id=TaskId.generate(),
            title="Due Today Task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=today,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        due_tomorrow = Task(
            id=TaskId.generate(),
            title="Due Tomorrow",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=today + timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(due_today.id.value, due_today)
        await cache.set(due_tomorrow.id.value, due_tomorrow)

        results = await service.send_due_notifications()

        assert results["discord"] == 1  # Only one task due today
        assert results["print"] == 1

    @pytest.mark.asyncio
    async def test_send_due_notifications_excludes_done(
        self, service, cache, mock_discord_sender
    ):
        """Should not send notifications for completed tasks."""
        today = datetime.now()
        done_task = Task(
            id=TaskId.generate(),
            title="Done Task",
            status=TaskStatus.DONE,
            source=TaskSource.MANUAL,
            due_date=today,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(done_task.id.value, done_task)

        results = await service.send_due_notifications()

        assert results["discord"] == 0

    @pytest.mark.asyncio
    async def test_send_overdue_notifications(
        self, service, cache, mock_discord_sender
    ):
        """Should send notifications for overdue tasks."""
        yesterday = datetime.now() - timedelta(days=1)
        overdue_task = Task(
            id=TaskId.generate(),
            title="Overdue Task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=yesterday,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(overdue_task.id.value, overdue_task)

        results = await service.send_overdue_notifications()

        assert results["discord"] == 1

    @pytest.mark.asyncio
    async def test_send_daily_summary(
        self, service, cache, mock_discord_sender
    ):
        """Should send daily summary with task counts."""
        # Add various tasks
        tasks = [
            Task(
                id=TaskId.generate(),
                title="TODO Task",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id=TaskId.generate(),
                title="In Progress Task",
                status=TaskStatus.IN_PROGRESS,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id=TaskId.generate(),
                title="Done Task",
                status=TaskStatus.DONE,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        for task in tasks:
            await cache.set(task.id.value, task)

        results = await service.send_daily_summary()

        assert results["discord"] is True
        call_args = mock_discord_sender.send.call_args
        notification = call_args[0][0]
        assert "Daily Task Summary" in notification.title
        assert "TODO: 1" in notification.message
        assert "In Progress: 1" in notification.message

    @pytest.mark.asyncio
    async def test_task_to_notification_with_metadata(self, service, cache):
        """Should include source info from task metadata."""
        task = Task(
            id=TaskId.generate(),
            title="Task from Slack",
            status=TaskStatus.TODO,
            source=TaskSource.SLACK_MENTION,
            metadata={
                "source_platform": "slack",
                "source_user_name": "john",
                "message_url": "https://slack.com/...",
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        notification = service._task_to_notification(
            task,
            title="Test",
            message="Test message",
        )

        assert notification.source_info == "slack - john"
        assert notification.task_url == "https://slack.com/..."

    @pytest.mark.asyncio
    async def test_send_with_partial_failure(
        self, service, mock_discord_sender, mock_print_sender
    ):
        """Should report partial success when some senders fail."""
        mock_discord_sender.send.return_value = True
        mock_print_sender.send.return_value = False

        notification = Notification(
            title="Test",
            message="Test",
            created_at=datetime.now(),
        )

        results = await service.send_notification(notification)

        assert results["discord"] is True
        assert results["print"] is False
