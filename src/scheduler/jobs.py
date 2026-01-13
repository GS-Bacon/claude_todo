"""Job definitions for the scheduler."""

import asyncio
from datetime import datetime
from typing import Callable, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Job:
    """Definition of a scheduled job."""

    name: str
    func: Callable[..., Any]
    cron: str  # Cron expression
    description: str = ""
    enabled: bool = True
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class JobRegistry:
    """Registry for managing scheduled jobs."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        cron: str,
        description: str = "",
        enabled: bool = True,
        args: tuple = (),
        kwargs: Optional[dict] = None,
    ) -> Job:
        """Register a new job.

        Args:
            name: Unique job name
            func: Function to execute
            cron: Cron expression for scheduling
            description: Job description
            enabled: Whether job is enabled
            args: Positional arguments for func
            kwargs: Keyword arguments for func

        Returns:
            Created Job instance
        """
        job = Job(
            name=name,
            func=func,
            cron=cron,
            description=description,
            enabled=enabled,
            args=args,
            kwargs=kwargs or {},
        )
        self._jobs[name] = job
        return job

    def unregister(self, name: str) -> bool:
        """Unregister a job by name.

        Args:
            name: Job name to remove

        Returns:
            True if removed, False if not found
        """
        if name in self._jobs:
            del self._jobs[name]
            return True
        return False

    def get(self, name: str) -> Optional[Job]:
        """Get job by name.

        Args:
            name: Job name

        Returns:
            Job if found, None otherwise
        """
        return self._jobs.get(name)

    def list_jobs(self) -> list[Job]:
        """List all registered jobs.

        Returns:
            List of all jobs
        """
        return list(self._jobs.values())

    def list_enabled(self) -> list[Job]:
        """List enabled jobs only.

        Returns:
            List of enabled jobs
        """
        return [job for job in self._jobs.values() if job.enabled]

    def enable(self, name: str) -> bool:
        """Enable a job.

        Args:
            name: Job name

        Returns:
            True if enabled, False if not found
        """
        job = self._jobs.get(name)
        if job:
            job.enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a job.

        Args:
            name: Job name

        Returns:
            True if disabled, False if not found
        """
        job = self._jobs.get(name)
        if job:
            job.enabled = False
            return True
        return False

    async def run_job(self, name: str) -> Any:
        """Run a job immediately.

        Args:
            name: Job name to run

        Returns:
            Result from job execution

        Raises:
            KeyError: If job not found
        """
        job = self._jobs.get(name)
        if not job:
            raise KeyError(f"Job not found: {name}")

        result = job.func(*job.args, **job.kwargs)
        if asyncio.iscoroutine(result):
            result = await result

        job.last_run = datetime.now()
        return result

    def clear(self) -> None:
        """Clear all registered jobs."""
        self._jobs.clear()


def create_default_jobs(registry: JobRegistry, container) -> None:
    """Create default jobs for the task management system.

    Args:
        registry: Job registry to add jobs to
        container: DI container for service access
    """

    async def sync_team_tasks():
        """Sync tasks from team Notion database."""
        service = container.task_service
        return await service.sync_from_team()

    async def sync_personal_tasks():
        """Sync tasks from personal Notion database."""
        service = container.task_service
        return await service.sync_from_personal()

    async def send_due_notifications():
        """Send notifications for tasks due today."""
        service = container.notification_service
        return await service.send_due_notifications()

    async def send_overdue_notifications():
        """Send notifications for overdue tasks."""
        service = container.notification_service
        return await service.send_overdue_notifications()

    async def send_daily_summary():
        """Send daily task summary."""
        service = container.notification_service
        return await service.send_daily_summary()

    # Register jobs
    registry.register(
        name="sync_team_tasks",
        func=sync_team_tasks,
        cron="*/15 * * * *",  # Every 15 minutes
        description="Sync tasks from team Notion database",
    )

    registry.register(
        name="sync_personal_tasks",
        func=sync_personal_tasks,
        cron="*/15 * * * *",  # Every 15 minutes
        description="Sync tasks from personal Notion database",
    )

    registry.register(
        name="send_due_notifications",
        func=send_due_notifications,
        cron="0 9 * * *",  # Every day at 9 AM
        description="Send notifications for tasks due today",
    )

    registry.register(
        name="send_overdue_notifications",
        func=send_overdue_notifications,
        cron="0 9,18 * * *",  # Every day at 9 AM and 6 PM
        description="Send notifications for overdue tasks",
    )

    registry.register(
        name="send_daily_summary",
        func=send_daily_summary,
        cron="0 8 * * 1-5",  # Weekdays at 8 AM
        description="Send daily task summary",
    )
