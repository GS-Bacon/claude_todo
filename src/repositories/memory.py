"""In-memory implementations of repositories for testing."""

from typing import Optional, Sequence

from src.domain.models import Task, TaskId, TaskFilter


class InMemoryTaskRepository:
    """In-memory implementation of TaskRepository for testing."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    async def get_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Retrieve a single task by ID."""
        return self._tasks.get(task_id.value)

    async def list_tasks(self, filter: Optional[TaskFilter] = None) -> Sequence[Task]:
        """List tasks matching filter criteria."""
        tasks = list(self._tasks.values())

        if filter is None:
            return tasks

        # Apply filters
        if filter.status:
            tasks = [t for t in tasks if t.status in filter.status]
        if filter.priority:
            tasks = [t for t in tasks if t.priority in filter.priority]
        if filter.source:
            tasks = [t for t in tasks if t.source in filter.source]
        if filter.assignee:
            tasks = [t for t in tasks if t.assignee == filter.assignee]
        if filter.due_before:
            tasks = [t for t in tasks if t.due_date and t.due_date < filter.due_before]
        if filter.due_after:
            tasks = [t for t in tasks if t.due_date and t.due_date > filter.due_after]
        if filter.tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in filter.tags)]

        # Apply pagination
        return tasks[filter.offset : filter.offset + filter.limit]

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        if task.id.value in self._tasks:
            raise ValueError(f"Task {task.id.value} already exists")
        self._tasks[task.id.value] = task
        return task

    async def update(self, task: Task) -> Task:
        """Update an existing task."""
        if task.id.value not in self._tasks:
            raise ValueError(f"Task {task.id.value} not found")
        self._tasks[task.id.value] = task
        return task

    async def delete(self, task_id: TaskId) -> bool:
        """Delete a task."""
        if task_id.value in self._tasks:
            del self._tasks[task_id.value]
            return True
        return False

    async def exists(self, task_id: TaskId) -> bool:
        """Check if a task exists."""
        return task_id.value in self._tasks


class InMemoryCacheRepository:
    """In-memory cache implementation."""

    def __init__(self) -> None:
        self._cache: dict[str, Task] = {}

    async def get(self, key: str) -> Optional[Task]:
        """Get cached task."""
        return self._cache.get(key)

    async def get_all(self) -> Sequence[Task]:
        """Get all cached tasks."""
        return list(self._cache.values())

    async def set(
        self, key: str, task: Task, ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache a task with optional TTL (TTL ignored in simple implementation)."""
        self._cache[key] = task

    async def set_many(
        self, tasks: dict[str, Task], ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache multiple tasks."""
        self._cache.update(tasks)

    async def invalidate(self, key: str) -> bool:
        """Remove item from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
