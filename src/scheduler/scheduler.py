"""Task scheduler using APScheduler."""

import asyncio
from datetime import datetime
from typing import Optional, Callable, Any
import logging

from .jobs import JobRegistry, Job

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler for running periodic tasks."""

    def __init__(
        self,
        registry: JobRegistry,
        timezone: str = "Asia/Tokyo",
    ):
        """Initialize scheduler.

        Args:
            registry: Job registry with registered jobs
            timezone: Timezone for cron scheduling
        """
        self._registry = registry
        self._timezone = timezone
        self._scheduler = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    @property
    def registry(self) -> JobRegistry:
        """Get the job registry."""
        return self._registry

    def start(self) -> None:
        """Start the scheduler.

        Requires APScheduler to be installed.
        """
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            raise ImportError(
                "APScheduler is required. Install with: pip install apscheduler"
            )

        if self._running:
            logger.warning("Scheduler already running")
            return

        self._scheduler = AsyncIOScheduler(timezone=self._timezone)

        # Add jobs from registry
        for job in self._registry.list_enabled():
            self._add_job_to_scheduler(job)

        self._scheduler.start()
        self._running = True
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running or not self._scheduler:
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Scheduler stopped")

    def _add_job_to_scheduler(self, job: Job) -> None:
        """Add a job to the APScheduler.

        Args:
            job: Job to add
        """
        if not self._scheduler:
            return

        from apscheduler.triggers.cron import CronTrigger

        async def wrapped_job():
            """Wrapper to handle async job execution."""
            try:
                result = job.func(*job.args, **job.kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                job.last_run = datetime.now()
                logger.info(f"Job {job.name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Job {job.name} failed: {e}")
                raise

        trigger = CronTrigger.from_crontab(job.cron, timezone=self._timezone)
        self._scheduler.add_job(
            wrapped_job,
            trigger=trigger,
            id=job.name,
            name=job.description or job.name,
            replace_existing=True,
        )
        logger.debug(f"Added job: {job.name} with cron: {job.cron}")

    def add_job(
        self,
        name: str,
        func: Callable[..., Any],
        cron: str,
        description: str = "",
    ) -> Job:
        """Add a new job to both registry and scheduler.

        Args:
            name: Job name
            func: Function to execute
            cron: Cron expression
            description: Job description

        Returns:
            Created Job
        """
        job = self._registry.register(
            name=name,
            func=func,
            cron=cron,
            description=description,
        )

        if self._running and self._scheduler:
            self._add_job_to_scheduler(job)

        return job

    def remove_job(self, name: str) -> bool:
        """Remove a job from scheduler and registry.

        Args:
            name: Job name to remove

        Returns:
            True if removed, False if not found
        """
        if self._running and self._scheduler:
            try:
                self._scheduler.remove_job(name)
            except Exception:
                pass

        return self._registry.unregister(name)

    def pause_job(self, name: str) -> bool:
        """Pause a job.

        Args:
            name: Job name

        Returns:
            True if paused, False if not found
        """
        if self._running and self._scheduler:
            try:
                self._scheduler.pause_job(name)
            except Exception:
                pass

        return self._registry.disable(name)

    def resume_job(self, name: str) -> bool:
        """Resume a paused job.

        Args:
            name: Job name

        Returns:
            True if resumed, False if not found
        """
        if not self._registry.enable(name):
            return False

        if self._running and self._scheduler:
            try:
                self._scheduler.resume_job(name)
            except Exception:
                # Job might not exist in scheduler yet
                job = self._registry.get(name)
                if job:
                    self._add_job_to_scheduler(job)

        return True

    async def run_job_now(self, name: str) -> Any:
        """Run a job immediately.

        Args:
            name: Job name

        Returns:
            Job result
        """
        return await self._registry.run_job(name)

    def get_job_status(self, name: str) -> Optional[dict]:
        """Get status of a job.

        Args:
            name: Job name

        Returns:
            Job status dict or None if not found
        """
        job = self._registry.get(name)
        if not job:
            return None

        status = {
            "name": job.name,
            "description": job.description,
            "cron": job.cron,
            "enabled": job.enabled,
            "last_run": job.last_run.isoformat() if job.last_run else None,
        }

        if self._running and self._scheduler:
            apjob = self._scheduler.get_job(name)
            if apjob:
                status["next_run"] = (
                    apjob.next_run_time.isoformat()
                    if apjob.next_run_time
                    else None
                )

        return status

    def list_jobs(self) -> list[dict]:
        """List all jobs with their status.

        Returns:
            List of job status dicts
        """
        return [
            status
            for job in self._registry.list_jobs()
            if (status := self.get_job_status(job.name))
        ]
