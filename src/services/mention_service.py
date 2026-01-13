"""Service for processing mentions and creating tasks."""

import re
from datetime import datetime
from typing import Optional

from src.domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskSource,
    TaskPriority,
    Mention,
)
from src.domain.protocols import TaskRepository, WebhookParser


class MentionService:
    """Service for processing mentions and creating tasks."""

    def __init__(
        self,
        personal_repository: TaskRepository,
        parsers: list[WebhookParser],
    ) -> None:
        self._repo = personal_repository
        self._parsers = {p.platform: p for p in parsers}

    def get_parser(self, payload: dict) -> Optional[WebhookParser]:
        """Find a parser that can handle the payload."""
        for parser in self._parsers.values():
            if parser.can_parse(payload):
                return parser
        return None

    def extract_task_details(self, mention: Mention) -> dict:
        """Extract task details from mention text.

        Supported formats:
        - !low, !medium, !high, !urgent -> priority
        - due:2024-01-15 -> due date
        - #tag -> tags
        """
        text = mention.message_text

        # Extract priority (e.g., !high, !urgent)
        priority = TaskPriority.MEDIUM
        priority_match = re.search(r"!(low|medium|high|urgent)", text, re.IGNORECASE)
        if priority_match:
            priority = TaskPriority(priority_match.group(1).lower())

        # Extract due date (e.g., due:2024-01-15)
        due_date = None
        due_match = re.search(r"due:(\d{4}-\d{2}-\d{2})", text)
        if due_match:
            try:
                due_date = datetime.strptime(due_match.group(1), "%Y-%m-%d")
            except ValueError:
                pass

        # Extract tags (e.g., #bug, #feature)
        tags = re.findall(r"#(\w+)", text)

        # Clean title (remove metadata)
        title = text
        title = re.sub(r"!(low|medium|high|urgent)", "", title, flags=re.IGNORECASE)
        title = re.sub(r"due:\S+", "", title)
        title = re.sub(r"#\w+", "", title)
        title = re.sub(r"<@\w+>", "", title)  # Remove Slack mentions
        title = re.sub(r"<@!\d+>", "", title)  # Remove Discord mentions
        title = " ".join(title.split())  # Normalize whitespace

        return {
            "title": title or "Task from mention",
            "priority": priority,
            "due_date": due_date,
            "tags": tags,
        }

    async def process_mention(self, mention: Mention) -> Task:
        """Process a mention and create a task."""
        details = self.extract_task_details(mention)

        source = (
            TaskSource.SLACK_MENTION
            if mention.source_platform == "slack"
            else TaskSource.DISCORD_MENTION
        )

        now = datetime.now()
        task = Task(
            id=TaskId.generate(),
            title=details["title"],
            description=f"From {mention.source_platform} by {mention.user_name}:\n\n{mention.message_text}",
            status=TaskStatus.TODO,
            source=source,
            priority=details["priority"],
            due_date=details["due_date"],
            tags=details["tags"],
            created_at=now,
            updated_at=now,
            metadata={
                "source_platform": mention.source_platform,
                "source_channel": mention.channel_id,
                "source_channel_name": mention.channel_name,
                "source_user_id": mention.user_id,
                "source_user_name": mention.user_name,
                "message_url": mention.message_url,
                "original_message": mention.message_text,
                "thread_context": mention.thread_context,
            },
        )

        return await self._repo.create(task)

    async def process_webhook(self, payload: dict) -> Optional[Task]:
        """Process a webhook payload end-to-end."""
        parser = self.get_parser(payload)
        if not parser:
            return None

        mention = parser.parse(payload)
        return await self.process_mention(mention)
