"""Domain models for the task management system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class TaskStatus(Enum):
    """Task status values."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskSource(Enum):
    """Source of the task."""

    NOTION_TEAM = "notion_team"
    NOTION_PERSONAL = "notion_personal"
    SLACK_MENTION = "slack_mention"
    DISCORD_MENTION = "discord_mention"
    MANUAL = "manual"


@dataclass(frozen=True)
class TaskId:
    """Value object for task identification."""

    value: str

    @classmethod
    def generate(cls) -> "TaskId":
        """Generate a new unique TaskId."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_notion(cls, notion_id: str) -> "TaskId":
        """Create a TaskId from a Notion page ID."""
        return cls(f"notion:{notion_id}")

    def __str__(self) -> str:
        return self.value


@dataclass
class Task:
    """Core task entity."""

    id: TaskId
    title: str
    status: TaskStatus
    source: TaskSource
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    external_id: Optional[str] = None  # Notion page ID, etc.
    metadata: dict = field(default_factory=dict)

    def is_due_today(self) -> bool:
        """Check if task is due today."""
        if not self.due_date:
            return False
        today = datetime.now().date()
        return self.due_date.date() == today

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False
        if self.status == TaskStatus.DONE:
            return False
        return self.due_date < datetime.now()


@dataclass(frozen=True)
class Mention:
    """Represents a parsed mention from Slack/Discord."""

    source_platform: str  # "slack" or "discord"
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    message_text: str
    timestamp: datetime
    message_url: str = ""
    thread_context: Optional[str] = None
    raw_payload: dict = field(default_factory=dict)


@dataclass
class Notification:
    """Notification to be sent."""

    title: str
    message: str
    created_at: datetime
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    task_url: Optional[str] = None
    source_info: Optional[str] = None
    channels: list[str] = field(default_factory=list)  # ["discord", "print"]
    scheduled_at: Optional[datetime] = None


@dataclass
class TaskFilter:
    """Filter criteria for task queries."""

    status: Optional[list[TaskStatus]] = None
    priority: Optional[list[TaskPriority]] = None
    source: Optional[list[TaskSource]] = None
    assignee: Optional[str] = None
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    tags: Optional[list[str]] = None
    limit: int = 100
    offset: int = 0
