"""Protocol definitions for dependency injection."""

from typing import Protocol, runtime_checkable, Optional, Sequence, Any

from .models import Task, TaskId, TaskFilter, Mention, Notification


@runtime_checkable
class TaskRepository(Protocol):
    """Protocol for task persistence operations."""

    async def get_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Retrieve a single task by ID."""
        ...

    async def list_tasks(self, filter: Optional[TaskFilter] = None) -> Sequence[Task]:
        """List tasks matching filter criteria."""
        ...

    async def create(self, task: Task) -> Task:
        """Create a new task, return the created task."""
        ...

    async def update(self, task: Task) -> Task:
        """Update an existing task, return the updated task."""
        ...

    async def delete(self, task_id: TaskId) -> bool:
        """Delete a task, return True if successful."""
        ...

    async def exists(self, task_id: TaskId) -> bool:
        """Check if a task exists."""
        ...


@runtime_checkable
class CacheRepository(Protocol):
    """Protocol for caching task data."""

    async def get(self, key: str) -> Optional[Task]:
        """Get cached task."""
        ...

    async def get_all(self) -> Sequence[Task]:
        """Get all cached tasks."""
        ...

    async def set(
        self, key: str, task: Task, ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache a task with optional TTL."""
        ...

    async def set_many(
        self, tasks: dict[str, Task], ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache multiple tasks."""
        ...

    async def invalidate(self, key: str) -> bool:
        """Remove item from cache."""
        ...

    async def clear(self) -> None:
        """Clear entire cache."""
        ...


@runtime_checkable
class NotificationSender(Protocol):
    """Protocol for sending notifications."""

    async def send(self, notification: Notification) -> bool:
        """Send a notification, return True if successful."""
        ...

    @property
    def channel_name(self) -> str:
        """Return the channel name this sender handles."""
        ...


@runtime_checkable
class WebhookParser(Protocol):
    """Protocol for parsing incoming webhooks."""

    def can_parse(self, payload: dict) -> bool:
        """Check if this parser can handle the payload."""
        ...

    def parse(self, payload: dict) -> Mention:
        """Parse webhook payload into a Mention."""
        ...

    @property
    def platform(self) -> str:
        """Return the platform name this parser handles."""
        ...
