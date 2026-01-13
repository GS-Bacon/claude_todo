"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from datetime import datetime, timedelta

from src.cli.main import cli
from src.container import get_container, reset_container
from src.repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository
from src.domain.models import Task, TaskId, TaskStatus, TaskPriority, TaskSource


@pytest.fixture(autouse=True)
def setup_container():
    """Set up container for each test."""
    reset_container()
    container = get_container()
    container.configure_task_repository(InMemoryTaskRepository)
    container.configure_personal_task_repository(InMemoryTaskRepository)
    container.configure_cache_repository(InMemoryCacheRepository)
    yield
    reset_container()


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_task():
    """Create sample task."""
    return Task(
        id=TaskId("test-123"),
        title="Test Task",
        description="Test description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        source=TaskSource.MANUAL,
        tags=["test"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class TestListCommand:
    """Tests for list command."""

    def test_list_empty(self, runner):
        """Should show no tasks message."""
        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "No tasks found" in result.output

    def test_list_tasks(self, runner, sample_task):
        """Should list tasks."""
        import asyncio
        container = get_container()
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "Test Task" in result.output

    def test_list_with_status_filter(self, runner, sample_task):
        """Should filter by status."""
        import asyncio
        container = get_container()
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        result = runner.invoke(cli, ["list", "--status", "todo"])

        assert result.exit_code == 0
        assert "Test Task" in result.output

    def test_list_invalid_status(self, runner):
        """Should show error for invalid status."""
        result = runner.invoke(cli, ["list", "--status", "invalid"])

        assert "Invalid status" in result.output

    def test_list_json_output(self, runner, sample_task):
        """Should output JSON when requested."""
        import asyncio
        container = get_container()
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        result = runner.invoke(cli, ["list", "--json"])

        assert result.exit_code == 0
        assert '"tasks"' in result.output
        assert '"total"' in result.output


class TestShowCommand:
    """Tests for show command."""

    def test_show_task(self, runner, sample_task):
        """Should show task details."""
        import asyncio
        container = get_container()
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        result = runner.invoke(cli, ["show", sample_task.id.value])

        assert result.exit_code == 0
        assert "Test Task" in result.output
        assert "todo" in result.output

    def test_show_task_not_found(self, runner):
        """Should show error when task not found."""
        result = runner.invoke(cli, ["show", "nonexistent"])

        assert "not found" in result.output


class TestCompleteCommand:
    """Tests for complete command."""

    def test_complete_task(self, runner, sample_task):
        """Should complete task."""
        import asyncio
        container = get_container()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )
        loop.run_until_complete(
            container.task_repository.create(sample_task)
        )

        result = runner.invoke(cli, ["complete", sample_task.id.value])

        assert result.exit_code == 0
        assert "completed" in result.output

    def test_complete_task_not_found(self, runner):
        """Should show error when task not found."""
        result = runner.invoke(cli, ["complete", "nonexistent"])

        assert "Error" in result.output


class TestSyncCommand:
    """Tests for sync command."""

    def test_sync_tasks(self, runner):
        """Should sync tasks."""
        result = runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "Synced" in result.output


class TestDueTodayCommand:
    """Tests for due-today command."""

    def test_due_today_empty(self, runner):
        """Should show no tasks message."""
        result = runner.invoke(cli, ["due-today"])

        assert result.exit_code == 0
        assert "No tasks due today" in result.output

    def test_due_today_with_tasks(self, runner):
        """Should show tasks due today."""
        import asyncio
        container = get_container()

        task = Task(
            id=TaskId.generate(),
            title="Due Today Task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(task.id.value, task)
        )

        result = runner.invoke(cli, ["due-today"])

        assert result.exit_code == 0
        assert "Due Today Task" in result.output


class TestOverdueCommand:
    """Tests for overdue command."""

    def test_overdue_empty(self, runner):
        """Should show no tasks message."""
        result = runner.invoke(cli, ["overdue"])

        assert result.exit_code == 0
        assert "No overdue tasks" in result.output

    def test_overdue_with_tasks(self, runner):
        """Should show overdue tasks."""
        import asyncio
        container = get_container()

        task = Task(
            id=TaskId.generate(),
            title="Overdue Task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() - timedelta(days=2),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(task.id.value, task)
        )

        result = runner.invoke(cli, ["overdue"])

        assert result.exit_code == 0
        assert "Overdue Task" in result.output


class TestJobsCommand:
    """Tests for jobs command."""

    def test_list_jobs(self, runner):
        """Should list jobs."""
        result = runner.invoke(cli, ["jobs"])

        assert result.exit_code == 0
        assert "sync_team_tasks" in result.output
        assert "sync_personal_tasks" in result.output


class TestRunJobCommand:
    """Tests for run-job command."""

    def test_run_job(self, runner):
        """Should run job."""
        result = runner.invoke(cli, ["run-job", "sync_team_tasks"])

        assert result.exit_code == 0
        assert "Job completed" in result.output

    def test_run_job_not_found(self, runner):
        """Should show error when job not found."""
        result = runner.invoke(cli, ["run-job", "nonexistent"])

        assert "not found" in result.output
        assert "Available jobs" in result.output


class TestSummaryCommand:
    """Tests for summary command."""

    def test_summary_empty(self, runner):
        """Should show no tasks message."""
        result = runner.invoke(cli, ["summary"])

        assert result.exit_code == 0
        assert "No tasks found" in result.output

    def test_summary_with_tasks(self, runner):
        """Should show summary."""
        import asyncio
        container = get_container()

        tasks = [
            Task(
                id=TaskId.generate(),
                title="TODO Task",
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id=TaskId.generate(),
                title="Done Task",
                status=TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        loop = asyncio.get_event_loop()
        for task in tasks:
            loop.run_until_complete(
                container.cache_repository.set(task.id.value, task)
            )

        result = runner.invoke(cli, ["summary"])

        assert result.exit_code == 0
        assert "Task Summary" in result.output
        assert "Total tasks" in result.output


class TestVersionOption:
    """Tests for version option."""

    def test_version(self, runner):
        """Should show version."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "1.0.0" in result.output
