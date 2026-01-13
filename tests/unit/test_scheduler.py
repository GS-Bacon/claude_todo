"""Tests for scheduler and job registry."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.scheduler.jobs import Job, JobRegistry, create_default_jobs
from src.scheduler.scheduler import TaskScheduler


class TestJob:
    """Tests for Job dataclass."""

    def test_job_creation(self):
        """Should create job with required fields."""
        def my_func():
            return "result"

        job = Job(
            name="test_job",
            func=my_func,
            cron="0 * * * *",
        )

        assert job.name == "test_job"
        assert job.func == my_func
        assert job.cron == "0 * * * *"
        assert job.enabled is True
        assert job.description == ""
        assert job.last_run is None

    def test_job_with_all_fields(self):
        """Should create job with all fields."""
        def my_func(x, y):
            return x + y

        job = Job(
            name="full_job",
            func=my_func,
            cron="*/5 * * * *",
            description="Test job",
            enabled=False,
            args=(1, 2),
            kwargs={"extra": True},
        )

        assert job.description == "Test job"
        assert job.enabled is False
        assert job.args == (1, 2)
        assert job.kwargs == {"extra": True}


class TestJobRegistry:
    """Tests for JobRegistry."""

    @pytest.fixture
    def registry(self):
        return JobRegistry()

    def test_register_job(self, registry):
        """Should register a new job."""
        def my_func():
            pass

        job = registry.register(
            name="test",
            func=my_func,
            cron="0 * * * *",
        )

        assert job.name == "test"
        assert registry.get("test") == job

    def test_unregister_job(self, registry):
        """Should unregister a job."""
        def my_func():
            pass

        registry.register(name="test", func=my_func, cron="0 * * * *")

        result = registry.unregister("test")

        assert result is True
        assert registry.get("test") is None

    def test_unregister_nonexistent(self, registry):
        """Should return False for nonexistent job."""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_job(self, registry):
        """Should get job by name."""
        def my_func():
            pass

        registry.register(name="test", func=my_func, cron="0 * * * *")

        job = registry.get("test")

        assert job is not None
        assert job.name == "test"

    def test_get_nonexistent_job(self, registry):
        """Should return None for nonexistent job."""
        result = registry.get("nonexistent")
        assert result is None

    def test_list_jobs(self, registry):
        """Should list all jobs."""
        def func1():
            pass

        def func2():
            pass

        registry.register(name="job1", func=func1, cron="0 * * * *")
        registry.register(name="job2", func=func2, cron="0 * * * *")

        jobs = registry.list_jobs()

        assert len(jobs) == 2
        assert any(j.name == "job1" for j in jobs)
        assert any(j.name == "job2" for j in jobs)

    def test_list_enabled_jobs(self, registry):
        """Should list only enabled jobs."""
        def func1():
            pass

        def func2():
            pass

        registry.register(name="enabled", func=func1, cron="0 * * * *", enabled=True)
        registry.register(name="disabled", func=func2, cron="0 * * * *", enabled=False)

        jobs = registry.list_enabled()

        assert len(jobs) == 1
        assert jobs[0].name == "enabled"

    def test_enable_job(self, registry):
        """Should enable a disabled job."""
        def my_func():
            pass

        registry.register(name="test", func=my_func, cron="0 * * * *", enabled=False)

        result = registry.enable("test")

        assert result is True
        assert registry.get("test").enabled is True

    def test_disable_job(self, registry):
        """Should disable an enabled job."""
        def my_func():
            pass

        registry.register(name="test", func=my_func, cron="0 * * * *", enabled=True)

        result = registry.disable("test")

        assert result is True
        assert registry.get("test").enabled is False

    def test_enable_nonexistent(self, registry):
        """Should return False for nonexistent job."""
        result = registry.enable("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_run_job_sync(self, registry):
        """Should run a sync job."""
        result_value = {"ran": True}

        def sync_func():
            return result_value

        registry.register(name="sync_job", func=sync_func, cron="0 * * * *")

        result = await registry.run_job("sync_job")

        assert result == result_value
        job = registry.get("sync_job")
        assert job.last_run is not None

    @pytest.mark.asyncio
    async def test_run_job_async(self, registry):
        """Should run an async job."""
        result_value = {"async_ran": True}

        async def async_func():
            return result_value

        registry.register(name="async_job", func=async_func, cron="0 * * * *")

        result = await registry.run_job("async_job")

        assert result == result_value

    @pytest.mark.asyncio
    async def test_run_nonexistent_job(self, registry):
        """Should raise KeyError for nonexistent job."""
        with pytest.raises(KeyError, match="not found"):
            await registry.run_job("nonexistent")

    def test_clear_jobs(self, registry):
        """Should clear all jobs."""
        def my_func():
            pass

        registry.register(name="job1", func=my_func, cron="0 * * * *")
        registry.register(name="job2", func=my_func, cron="0 * * * *")

        registry.clear()

        assert len(registry.list_jobs()) == 0


class TestCreateDefaultJobs:
    """Tests for create_default_jobs function."""

    def test_creates_default_jobs(self):
        """Should create default jobs in registry."""
        registry = JobRegistry()
        mock_container = MagicMock()
        mock_container.task_service = MagicMock()
        mock_container.notification_service = MagicMock()

        create_default_jobs(registry, mock_container)

        jobs = registry.list_jobs()
        job_names = [j.name for j in jobs]

        assert "sync_team_tasks" in job_names
        assert "sync_personal_tasks" in job_names
        assert "send_due_notifications" in job_names
        assert "send_overdue_notifications" in job_names
        assert "send_daily_summary" in job_names


class TestTaskScheduler:
    """Tests for TaskScheduler."""

    @pytest.fixture
    def registry(self):
        return JobRegistry()

    @pytest.fixture
    def scheduler(self, registry):
        return TaskScheduler(registry)

    def test_initial_state(self, scheduler):
        """Should start in stopped state."""
        assert scheduler.is_running is False

    def test_registry_property(self, scheduler, registry):
        """Should return the registry."""
        assert scheduler.registry is registry

    def test_add_job(self, scheduler):
        """Should add job to registry."""
        def my_func():
            pass

        job = scheduler.add_job(
            name="test",
            func=my_func,
            cron="0 * * * *",
            description="Test job",
        )

        assert job.name == "test"
        assert scheduler.registry.get("test") is not None

    def test_remove_job(self, scheduler):
        """Should remove job from registry."""
        def my_func():
            pass

        scheduler.add_job(name="test", func=my_func, cron="0 * * * *")

        result = scheduler.remove_job("test")

        assert result is True
        assert scheduler.registry.get("test") is None

    def test_pause_job(self, scheduler):
        """Should pause job."""
        def my_func():
            pass

        scheduler.add_job(name="test", func=my_func, cron="0 * * * *")

        result = scheduler.pause_job("test")

        assert result is True
        assert scheduler.registry.get("test").enabled is False

    def test_resume_job(self, scheduler):
        """Should resume job."""
        def my_func():
            pass

        scheduler.add_job(name="test", func=my_func, cron="0 * * * *")
        scheduler.pause_job("test")

        result = scheduler.resume_job("test")

        assert result is True
        assert scheduler.registry.get("test").enabled is True

    @pytest.mark.asyncio
    async def test_run_job_now(self, scheduler):
        """Should run job immediately."""
        result_value = "executed"

        async def my_func():
            return result_value

        scheduler.add_job(name="test", func=my_func, cron="0 * * * *")

        result = await scheduler.run_job_now("test")

        assert result == result_value

    def test_get_job_status(self, scheduler):
        """Should return job status."""
        def my_func():
            pass

        scheduler.add_job(
            name="test",
            func=my_func,
            cron="0 * * * *",
            description="Test job",
        )

        status = scheduler.get_job_status("test")

        assert status is not None
        assert status["name"] == "test"
        assert status["description"] == "Test job"
        assert status["cron"] == "0 * * * *"
        assert status["enabled"] is True
        assert status["last_run"] is None

    def test_get_job_status_nonexistent(self, scheduler):
        """Should return None for nonexistent job."""
        status = scheduler.get_job_status("nonexistent")
        assert status is None

    def test_list_jobs(self, scheduler):
        """Should list all jobs."""
        def func1():
            pass

        def func2():
            pass

        scheduler.add_job(name="job1", func=func1, cron="0 * * * *")
        scheduler.add_job(name="job2", func=func2, cron="*/5 * * * *")

        jobs = scheduler.list_jobs()

        assert len(jobs) == 2
        names = [j["name"] for j in jobs]
        assert "job1" in names
        assert "job2" in names
