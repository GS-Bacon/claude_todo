"""Discord webhook parser."""

from datetime import datetime

from src.domain.models import Mention


class DiscordWebhookParser:
    """Parse Discord webhook payloads."""

    @property
    def platform(self) -> str:
        return "discord"

    def can_parse(self, payload: dict) -> bool:
        """Check if payload is from Discord."""
        # Discord interaction or message create event
        return "type" in payload and (
            "guild_id" in payload or "channel_id" in payload
        )

    def parse(self, payload: dict) -> Mention:
        """Parse Discord event into Mention."""
        # Handle different Discord event formats
        author = payload.get("author", {})
        channel = payload.get("channel", {})

        # Extract timestamp
        timestamp_str = payload.get("timestamp")
        if timestamp_str:
            try:
                # Discord uses ISO format with Z suffix
                timestamp = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Build message URL
        guild_id = payload.get("guild_id", "")
        channel_id = payload.get("channel_id", "")
        message_id = payload.get("id", "")
        message_url = ""
        if guild_id and channel_id and message_id:
            message_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

        return Mention(
            source_platform="discord",
            channel_id=channel_id,
            channel_name=channel.get("name", ""),
            user_id=author.get("id", ""),
            user_name=author.get("username", ""),
            message_text=payload.get("content", ""),
            timestamp=timestamp,
            message_url=message_url,
            thread_context=payload.get("message_reference", {}).get("message_id"),
            raw_payload=payload,
        )
