"""Slack webhook parser."""

from datetime import datetime

from src.domain.models import Mention


class SlackWebhookParser:
    """Parse Slack webhook payloads."""

    @property
    def platform(self) -> str:
        return "slack"

    def can_parse(self, payload: dict) -> bool:
        """Check if payload is from Slack."""
        return (
            "event" in payload
            and payload.get("type") == "event_callback"
            and payload.get("event", {}).get("type") in ("app_mention", "message")
        )

    def parse(self, payload: dict) -> Mention:
        """Parse Slack event into Mention."""
        event = payload.get("event", {})

        # Extract timestamp
        ts = event.get("ts", "0")
        try:
            timestamp = datetime.fromtimestamp(float(ts))
        except (ValueError, TypeError):
            timestamp = datetime.now()

        # Build message URL
        team_id = payload.get("team_id", "")
        channel_id = event.get("channel", "")
        message_ts = ts.replace(".", "")
        message_url = ""
        if team_id and channel_id and message_ts:
            message_url = f"https://slack.com/archives/{channel_id}/p{message_ts}"

        return Mention(
            source_platform="slack",
            channel_id=channel_id,
            channel_name=event.get("channel_name", ""),
            user_id=event.get("user", ""),
            user_name=event.get("user_name", ""),
            message_text=event.get("text", ""),
            timestamp=timestamp,
            message_url=message_url,
            thread_context=event.get("thread_ts"),
            raw_payload=payload,
        )
