"""Webhook parsers for different platforms."""

from .slack_parser import SlackWebhookParser
from .discord_parser import DiscordWebhookParser

__all__ = [
    "SlackWebhookParser",
    "DiscordWebhookParser",
]
