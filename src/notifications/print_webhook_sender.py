"""Print webhook notification sender implementation."""

from typing import Optional
import httpx

from ..domain.models import Notification


class PrintWebhookSender:
    """Sends notifications to a custom print server via HTTP webhook."""

    def __init__(
        self,
        webhook_url: str,
        *,
        api_key: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize print webhook sender.

        Args:
            webhook_url: Print server webhook URL
            api_key: Optional API key for authentication
            http_client: Optional HTTP client for testing
        """
        self._webhook_url = webhook_url
        self._api_key = api_key
        self._http_client = http_client
        self._owns_client = http_client is None

    @property
    def channel_name(self) -> str:
        """Return channel name for this sender."""
        return "print"

    async def send(self, notification: Notification) -> bool:
        """Send notification to print server.

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully, False otherwise
        """
        payload = self._build_payload(notification)
        headers = self._build_headers()

        client = self._http_client or httpx.AsyncClient()
        try:
            response = await client.post(
                self._webhook_url,
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            return response.status_code in (200, 201, 202, 204)
        except httpx.HTTPError:
            return False
        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    def _build_payload(self, notification: Notification) -> dict:
        """Build print webhook payload.

        Args:
            notification: Notification to convert

        Returns:
            Print webhook payload dict
        """
        payload = {
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.created_at.isoformat(),
        }

        # Add optional fields
        if notification.priority:
            payload["priority"] = notification.priority.value

        if notification.due_date:
            payload["due_date"] = notification.due_date.isoformat()

        if notification.task_url:
            payload["task_url"] = notification.task_url

        if notification.source_info:
            payload["source"] = notification.source_info

        # Format for printing
        payload["formatted_text"] = self._format_for_print(notification)

        return payload

    def _build_headers(self) -> dict:
        """Build HTTP headers.

        Returns:
            Headers dict
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _format_for_print(self, notification: Notification) -> str:
        """Format notification for print output.

        Args:
            notification: Notification to format

        Returns:
            Formatted text string
        """
        lines = [
            "=" * 40,
            f"📋 {notification.title}",
            "-" * 40,
            notification.message,
        ]

        if notification.priority:
            priority_icons = {
                "low": "🟢",
                "medium": "🔵",
                "high": "🟠",
                "urgent": "🔴",
            }
            icon = priority_icons.get(notification.priority.value, "⚪")
            lines.append(f"Priority: {icon} {notification.priority.value.upper()}")

        if notification.due_date:
            lines.append(f"Due: {notification.due_date.strftime('%Y-%m-%d %H:%M')}")

        if notification.source_info:
            lines.append(f"Source: {notification.source_info}")

        lines.append("-" * 40)
        lines.append(f"Time: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 40)

        return "\n".join(lines)
