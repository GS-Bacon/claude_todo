"""Notification service for sending task notifications."""

from datetime import datetime
from typing import Optional, Sequence

from ..domain.models import (
    Notification,
    Task,
    TaskFilter,
    TaskPriority,
    TaskStatus,
)
from ..domain.protocols import CacheRepository, NotificationSender


class NotificationService:
    """Service for managing and sending notifications."""

    def __init__(
        self,
        cache_repository: CacheRepository,
        senders: Sequence[NotificationSender],
    ):
        """Initialize notification service.

        Args:
            cache_repository: Cache repository for tasks
            senders: List of notification senders
        """
        self._cache = cache_repository
        self._senders = list(senders)

    @property
    def senders(self) -> list[NotificationSender]:
        """Get list of registered senders."""
        return self._senders

    def add_sender(self, sender: NotificationSender) -> None:
        """Add a notification sender.

        Args:
            sender: Sender to add
        """
        self._senders.append(sender)

    def remove_sender(self, channel_name: str) -> bool:
        """Remove a sender by channel name.

        Args:
            channel_name: Name of the channel to remove

        Returns:
            True if removed, False if not found
        """
        for i, sender in enumerate(self._senders):
            if sender.channel_name == channel_name:
                del self._senders[i]
                return True
        return False

    async def send_notification(
        self,
        notification: Notification,
        channels: Optional[Sequence[str]] = None,
    ) -> dict[str, bool]:
        """Send notification to specified channels.

        Args:
            notification: Notification to send
            channels: Channel names to send to, or None for all

        Returns:
            Dict mapping channel names to success status
        """
        results = {}

        for sender in self._senders:
            if channels is None or sender.channel_name in channels:
                success = await sender.send(notification)
                results[sender.channel_name] = success

        return results

    async def send_task_reminder(
        self,
        task: Task,
        message: Optional[str] = None,
        channels: Optional[Sequence[str]] = None,
    ) -> dict[str, bool]:
        """Send reminder notification for a task.

        Args:
            task: Task to send reminder for
            message: Optional custom message
            channels: Channels to send to

        Returns:
            Dict mapping channel names to success status
        """
        notification = self._task_to_notification(
            task,
            title=f"Task Reminder: {task.title}",
            message=message or self._build_reminder_message(task),
        )
        return await self.send_notification(notification, channels)

    async def send_due_notifications(
        self,
        channels: Optional[Sequence[str]] = None,
    ) -> dict[str, int]:
        """Send notifications for tasks due today.

        Args:
            channels: Channels to send to

        Returns:
            Dict mapping channel names to number of notifications sent
        """
        today = datetime.now().date()
        all_tasks = await self._cache.get_all()

        due_tasks = [
            task for task in all_tasks
            if task.due_date is not None
            and task.due_date.date() == today
            and task.status not in (TaskStatus.DONE,)
        ]

        sent_counts: dict[str, int] = {
            sender.channel_name: 0
            for sender in self._senders
            if channels is None or sender.channel_name in channels
        }

        for task in due_tasks:
            notification = self._task_to_notification(
                task,
                title=f"Due Today: {task.title}",
                message=self._build_due_today_message(task),
            )
            results = await self.send_notification(notification, channels)
            for channel, success in results.items():
                if success:
                    sent_counts[channel] = sent_counts.get(channel, 0) + 1

        return sent_counts

    async def send_overdue_notifications(
        self,
        channels: Optional[Sequence[str]] = None,
    ) -> dict[str, int]:
        """Send notifications for overdue tasks.

        Args:
            channels: Channels to send to

        Returns:
            Dict mapping channel names to number of notifications sent
        """
        now = datetime.now()
        all_tasks = await self._cache.get_all()

        overdue_tasks = [
            task for task in all_tasks
            if task.due_date is not None
            and task.due_date < now
            and task.status not in (TaskStatus.DONE,)
        ]

        sent_counts: dict[str, int] = {
            sender.channel_name: 0
            for sender in self._senders
            if channels is None or sender.channel_name in channels
        }

        for task in overdue_tasks:
            notification = self._task_to_notification(
                task,
                title=f"⚠️ Overdue: {task.title}",
                message=self._build_overdue_message(task),
            )
            results = await self.send_notification(notification, channels)
            for channel, success in results.items():
                if success:
                    sent_counts[channel] = sent_counts.get(channel, 0) + 1

        return sent_counts

    async def send_daily_summary(
        self,
        channels: Optional[Sequence[str]] = None,
    ) -> dict[str, bool]:
        """Send daily task summary.

        Args:
            channels: Channels to send to

        Returns:
            Dict mapping channel names to success status
        """
        all_tasks = await self._cache.get_all()
        today = datetime.now().date()

        # Count tasks by status
        todo_count = sum(1 for t in all_tasks if t.status == TaskStatus.TODO)
        in_progress_count = sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS)
        done_today = sum(
            1 for t in all_tasks
            if t.status == TaskStatus.DONE
            and t.updated_at.date() == today
        )

        # Count due today and overdue
        due_today = sum(
            1 for t in all_tasks
            if t.due_date and t.due_date.date() == today
            and t.status != TaskStatus.DONE
        )
        overdue = sum(
            1 for t in all_tasks
            if t.due_date and t.due_date.date() < today
            and t.status != TaskStatus.DONE
        )

        message_lines = [
            f"📊 **Daily Task Summary** - {today.strftime('%Y-%m-%d')}",
            "",
            f"📋 TODO: {todo_count}",
            f"🔄 In Progress: {in_progress_count}",
            f"✅ Completed Today: {done_today}",
            "",
        ]

        if due_today > 0:
            message_lines.append(f"⏰ Due Today: {due_today}")
        if overdue > 0:
            message_lines.append(f"⚠️ Overdue: {overdue}")

        notification = Notification(
            title="Daily Task Summary",
            message="\n".join(message_lines),
            created_at=datetime.now(),
        )

        return await self.send_notification(notification, channels)

    def _task_to_notification(
        self,
        task: Task,
        title: str,
        message: str,
    ) -> Notification:
        """Convert task to notification.

        Args:
            task: Task to convert
            title: Notification title
            message: Notification message

        Returns:
            Notification object
        """
        # Build source info
        source_info = None
        if task.metadata:
            platform = task.metadata.get("source_platform")
            user = task.metadata.get("source_user_name")
            if platform and user:
                source_info = f"{platform} - {user}"

        return Notification(
            title=title,
            message=message,
            priority=task.priority,
            due_date=task.due_date,
            task_url=task.metadata.get("message_url") if task.metadata else None,
            source_info=source_info,
            created_at=datetime.now(),
        )

    def _build_reminder_message(self, task: Task) -> str:
        """Build reminder message for task.

        Args:
            task: Task to build message for

        Returns:
            Message string
        """
        lines = [task.description or "No description provided."]

        if task.due_date:
            lines.append(f"\n📅 Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}")

        if task.tags:
            lines.append(f"🏷️ Tags: {', '.join(task.tags)}")

        return "\n".join(lines)

    def _build_due_today_message(self, task: Task) -> str:
        """Build due today message for task.

        Args:
            task: Task to build message for

        Returns:
            Message string
        """
        lines = [
            f"This task is due today!",
            "",
            task.description or "No description provided.",
        ]

        if task.due_date:
            lines.append(f"\n⏰ Due at: {task.due_date.strftime('%H:%M')}")

        return "\n".join(lines)

    def _build_overdue_message(self, task: Task) -> str:
        """Build overdue message for task.

        Args:
            task: Task to build message for

        Returns:
            Message string
        """
        days_overdue = (datetime.now() - task.due_date).days if task.due_date else 0

        lines = [
            f"This task is overdue by {days_overdue} day(s)!",
            "",
            task.description or "No description provided.",
        ]

        if task.due_date:
            lines.append(f"\n📅 Was due: {task.due_date.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(lines)
