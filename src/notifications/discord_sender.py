"""Discord notification sender implementation."""

from typing import Optional
import httpx

from ..domain.models import Notification, TaskPriority


class DiscordNotificationSender:
    """Sends notifications to Discord via webhook."""

    def __init__(
        self,
        webhook_url: str,
        *,
        username: str = "Task Manager",
        avatar_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize Discord sender.

        Args:
            webhook_url: Discord webhook URL
            username: Bot username to display
            avatar_url: Optional avatar URL for the bot
            http_client: Optional HTTP client for testing
        """
        self._webhook_url = webhook_url
        self._username = username
        self._avatar_url = avatar_url
        self._http_client = http_client
        self._owns_client = http_client is None

    @property
    def channel_name(self) -> str:
        """Return channel name for this sender."""
        return "discord"

    async def send(self, notification: Notification) -> bool:
        """Send notification to Discord.

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully, False otherwise
        """
        payload = self._build_payload(notification)

        client = self._http_client or httpx.AsyncClient()
        try:
            response = await client.post(
                self._webhook_url,
                json=payload,
                timeout=10.0,
            )
            return response.status_code in (200, 204)
        except httpx.HTTPError:
            return False
        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    def _build_payload(self, notification: Notification) -> dict:
        """Build Discord webhook payload with embed.

        Args:
            notification: Notification to convert

        Returns:
            Discord webhook payload dict
        """
        color = self._get_color_for_priority(notification.priority)

        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": color,
            "fields": [],
        }

        # Add task link if available
        if notification.task_url:
            embed["url"] = notification.task_url

        # Add priority field
        if notification.priority:
            embed["fields"].append({
                "name": "Priority",
                "value": notification.priority.value.capitalize(),
                "inline": True,
            })

        # Add due date field
        if notification.due_date:
            embed["fields"].append({
                "name": "Due Date",
                "value": notification.due_date.strftime("%Y-%m-%d %H:%M"),
                "inline": True,
            })

        # Add source info
        if notification.source_info:
            embed["fields"].append({
                "name": "Source",
                "value": notification.source_info,
                "inline": True,
            })

        # Add timestamp
        embed["timestamp"] = notification.created_at.isoformat()

        payload = {
            "username": self._username,
            "embeds": [embed],
        }

        if self._avatar_url:
            payload["avatar_url"] = self._avatar_url

        return payload

    def _get_color_for_priority(self, priority: Optional[TaskPriority]) -> int:
        """Get Discord embed color based on priority.

        Args:
            priority: Task priority

        Returns:
            Discord color integer
        """
        if priority is None:
            return 0x808080  # Gray

        colors = {
            TaskPriority.LOW: 0x2ECC71,      # Green
            TaskPriority.MEDIUM: 0x3498DB,   # Blue
            TaskPriority.HIGH: 0xF39C12,     # Orange
            TaskPriority.URGENT: 0xE74C3C,   # Red
        }
        return colors.get(priority, 0x808080)
