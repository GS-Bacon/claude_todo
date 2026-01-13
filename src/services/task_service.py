"""Task service with caching support."""

from dataclasses import replace
from datetime import datetime
from typing import Optional, Sequence

from src.domain.models import Task, TaskId, TaskFilter, TaskStatus
from src.domain.protocols import TaskRepository, CacheRepository


class TaskService:
    """Task service orchestrating repositories and cache."""

    def __init__(
        self,
        team_repository: TaskRepository,
        personal_repository: TaskRepository,
        cache: CacheRepository,
    ) -> None:
        self._team_repo = team_repository
        self._personal_repo = personal_repository
        self._cache = cache

    async def get_task(self, task_id: TaskId) -> Optional[Task]:
        """Get task from cache, falling back to repositories."""
        # Try cache first
        cached = await self._cache.get(task_id.value)
        if cached:
            return cached

        # Try team repository
        task = await self._team_repo.get_by_id(task_id)
        if not task:
            # Try personal repository
            task = await self._personal_repo.get_by_id(task_id)

        if task:
            await self._cache.set(task_id.value, task)

        return task

    async def list_tasks(self, filter: Optional[TaskFilter] = None) -> Sequence[Task]:
        """List tasks from cache with optional filtering."""
        all_tasks = list(await self._cache.get_all())

        if filter is None:
            return all_tasks

        result = all_tasks

        if filter.status:
            result = [t for t in result if t.status in filter.status]
        if filter.priority:
            result = [t for t in result if t.priority in filter.priority]
        if filter.source:
            result = [t for t in result if t.source in filter.source]
        if filter.assignee:
            result = [t for t in result if t.assignee == filter.assignee]
        if filter.due_before:
            result = [t for t in result if t.due_date and t.due_date < filter.due_before]
        if filter.due_after:
            result = [t for t in result if t.due_date and t.due_date > filter.due_after]
        if filter.tags:
            result = [t for t in result if any(tag in t.tags for tag in filter.tags)]

        return result[filter.offset : filter.offset + filter.limit]

    async def create_task(self, task: Task, personal: bool = False) -> Task:
        """Create a new task in the appropriate repository."""
        repo = self._personal_repo if personal else self._team_repo
        created = await repo.create(task)
        await self._cache.set(created.id.value, created)
        return created

    async def update_task(self, task: Task) -> Task:
        """Update a task and refresh cache."""
        # Determine which repository has the task
        if await self._team_repo.exists(task.id):
            updated = await self._team_repo.update(task)
        elif await self._personal_repo.exists(task.id):
            updated = await self._personal_repo.update(task)
        else:
            raise ValueError(f"Task {task.id.value} not found in any repository")

        await self._cache.set(updated.id.value, updated)
        return updated

    async def update_task_status(self, task_id: TaskId, status: TaskStatus) -> Task:
        """Update a task's status."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id.value} not found")

        updated_task = replace(task, status=status, updated_at=datetime.now())
        return await self.update_task(updated_task)

    async def delete_task(self, task_id: TaskId) -> bool:
        """Delete a task from the appropriate repository."""
        # Try team repository first
        if await self._team_repo.delete(task_id):
            await self._cache.invalidate(task_id.value)
            return True

        # Try personal repository
        if await self._personal_repo.delete(task_id):
            await self._cache.invalidate(task_id.value)
            return True

        return False

    async def sync_from_team(self) -> int:
        """Sync all tasks from team repository to cache."""
        tasks = await self._team_repo.list_tasks()
        task_dict = {t.id.value: t for t in tasks}
        await self._cache.set_many(task_dict)
        return len(tasks)

    async def sync_from_personal(self) -> int:
        """Sync all tasks from personal repository to cache."""
        tasks = await self._personal_repo.list_tasks()
        task_dict = {t.id.value: t for t in tasks}
        await self._cache.set_many(task_dict)
        return len(tasks)

    async def sync_all(self) -> dict[str, int]:
        """Sync tasks from all repositories."""
        team_count = await self.sync_from_team()
        personal_count = await self.sync_from_personal()
        return {
            "team_tasks": team_count,
            "personal_tasks": personal_count,
        }

    async def get_tasks_due_today(self) -> Sequence[Task]:
        """Get all tasks due today."""
        all_tasks = await self._cache.get_all()
        return [t for t in all_tasks if t.is_due_today()]

    async def get_overdue_tasks(self) -> Sequence[Task]:
        """Get all overdue tasks."""
        all_tasks = await self._cache.get_all()
        return [t for t in all_tasks if t.is_overdue()]
