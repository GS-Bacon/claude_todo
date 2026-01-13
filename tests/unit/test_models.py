"""Tests for domain models."""

import pytest
from datetime import datetime, timedelta

from src.domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskPriority,
    TaskSource,
    TaskFilter,
    Mention,
    Notification,
)


class TestTaskId:
    """Tests for TaskId value object."""

    def test_generate_creates_unique_ids(self):
        """Generated IDs should be unique."""
        id1 = TaskId.generate()
        id2 = TaskId.generate()
        assert id1.value != id2.value

    def test_from_notion_prefixes_correctly(self):
        """Notion IDs should be prefixed with 'notion:'."""
        notion_id = "abc-123-def"
        task_id = TaskId.from_notion(notion_id)
        assert task_id.value == "notion:abc-123-def"

    def test_task_id_is_immutable(self):
        """TaskId should be immutable (frozen dataclass)."""
        task_id = TaskId.generate()
        with pytest.raises(AttributeError):
            task_id.value = "new_value"

    def test_str_returns_value(self):
        """str() should return the value."""
        task_id = TaskId("test-id-123")
        assert str(task_id) == "test-id-123"


class TestTask:
    """Tests for Task entity."""

    def test_task_creation_with_defaults(self):
        """Task should have sensible defaults."""
        task = Task(
            id=TaskId.generate(),
            title="Test task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.priority == TaskPriority.MEDIUM
        assert task.tags == []
        assert task.description is None
        assert task.due_date is None
        assert task.assignee is None
        assert task.metadata == {}

    def test_is_due_today_returns_true_for_today(self):
        """is_due_today should return True for tasks due today."""
        task = Task(
            id=TaskId.generate(),
            title="Due today",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.is_due_today() is True

    def test_is_due_today_returns_false_for_tomorrow(self):
        """is_due_today should return False for tasks due tomorrow."""
        task = Task(
            id=TaskId.generate(),
            title="Due tomorrow",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() + timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.is_due_today() is False

    def test_is_due_today_returns_false_when_no_due_date(self):
        """is_due_today should return False when there's no due date."""
        task = Task(
            id=TaskId.generate(),
            title="No due date",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.is_due_today() is False

    def test_is_overdue_returns_true_for_past_date(self):
        """is_overdue should return True for tasks with past due dates."""
        task = Task(
            id=TaskId.generate(),
            title="Overdue",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() - timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.is_overdue() is True

    def test_is_overdue_returns_false_for_done_tasks(self):
        """is_overdue should return False for completed tasks."""
        task = Task(
            id=TaskId.generate(),
            title="Done but overdue",
            status=TaskStatus.DONE,
            source=TaskSource.MANUAL,
            due_date=datetime.now() - timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.is_overdue() is False

    def test_is_overdue_returns_false_when_no_due_date(self):
        """is_overdue should return False when there's no due date."""
        task = Task(
            id=TaskId.generate(),
            title="No due date",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert task.is_overdue() is False


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_have_string_values(self):
        """All status values should be strings."""
        for status in TaskStatus:
            assert isinstance(status.value, str)

    def test_status_values(self):
        """Status values should match expected strings."""
        assert TaskStatus.TODO.value == "todo"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.DONE.value == "done"
        assert TaskStatus.BLOCKED.value == "blocked"


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_ordering(self):
        """Priority values should be comparable."""
        priorities = [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.URGENT]
        priority_values = ["low", "medium", "high", "urgent"]
        for p, v in zip(priorities, priority_values):
            assert p.value == v


class TestTaskSource:
    """Tests for TaskSource enum."""

    def test_source_values(self):
        """Source values should match expected strings."""
        assert TaskSource.NOTION_TEAM.value == "notion_team"
        assert TaskSource.NOTION_PERSONAL.value == "notion_personal"
        assert TaskSource.SLACK_MENTION.value == "slack_mention"
        assert TaskSource.DISCORD_MENTION.value == "discord_mention"
        assert TaskSource.MANUAL.value == "manual"


class TestMention:
    """Tests for Mention dataclass."""

    def test_mention_creation(self):
        """Mention should be created with all fields."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Please review this",
            timestamp=datetime.now(),
            message_url="https://slack.com/...",
            thread_context="Parent message",
            raw_payload={"type": "event_callback"},
        )
        assert mention.source_platform == "slack"
        assert mention.channel_id == "C123"
        assert mention.user_name == "john"

    def test_mention_is_immutable(self):
        """Mention should be immutable (frozen dataclass)."""
        mention = Mention(
            source_platform="slack",
            channel_id="C123",
            channel_name="general",
            user_id="U456",
            user_name="john",
            message_text="Test",
            timestamp=datetime.now(),
        )
        with pytest.raises(AttributeError):
            mention.source_platform = "discord"


class TestNotification:
    """Tests for Notification dataclass."""

    def test_notification_creation(self, sample_task):
        """Notification should be created with required fields."""
        notification = Notification(
            title="Task Reminder",
            message="Remember to complete the task",
            created_at=datetime.now(),
            channels=["discord", "print"],
        )
        assert notification.title == "Task Reminder"
        assert notification.message == "Remember to complete the task"
        assert "discord" in notification.channels
        assert "print" in notification.channels
        assert notification.scheduled_at is None
        assert notification.priority is None
        assert notification.due_date is None

    def test_notification_with_optional_fields(self, sample_task):
        """Notification should accept optional fields."""
        due = datetime(2024, 1, 15, 14, 0)
        notification = Notification(
            title="Urgent Task",
            message="Task is urgent",
            created_at=datetime.now(),
            priority=TaskPriority.HIGH,
            due_date=due,
            task_url="https://notion.so/task/123",
            source_info="slack - john",
        )
        assert notification.priority == TaskPriority.HIGH
        assert notification.due_date == due
        assert notification.task_url == "https://notion.so/task/123"
        assert notification.source_info == "slack - john"


class TestTaskFilter:
    """Tests for TaskFilter dataclass."""

    def test_filter_defaults(self):
        """TaskFilter should have sensible defaults."""
        filter = TaskFilter()
        assert filter.status is None
        assert filter.priority is None
        assert filter.source is None
        assert filter.limit == 100
        assert filter.offset == 0

    def test_filter_with_status(self):
        """TaskFilter should accept status list."""
        filter = TaskFilter(status=[TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        assert len(filter.status) == 2
        assert TaskStatus.TODO in filter.status

    def test_filter_with_date_range(self):
        """TaskFilter should accept date ranges."""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        filter = TaskFilter(due_after=now, due_before=tomorrow)
        assert filter.due_after == now
        assert filter.due_before == tomorrow
