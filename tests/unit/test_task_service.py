"""Tests for TaskService."""

import pytest
from datetime import datetime, timedelta
from dataclasses import replace

from src.services.task_service import TaskService
from src.repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository
from src.domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskSource,
    TaskPriority,
    TaskFilter,
)


class TestTaskService:
    """Tests for TaskService."""

    @pytest.fixture
    def team_repo(self) -> InMemoryTaskRepository:
        return InMemoryTaskRepository()

    @pytest.fixture
    def personal_repo(self) -> InMemoryTaskRepository:
        return InMemoryTaskRepository()

    @pytest.fixture
    def cache(self) -> InMemoryCacheRepository:
        return InMemoryCacheRepository()

    @pytest.fixture
    def service(self, team_repo, personal_repo, cache) -> TaskService:
        return TaskService(team_repo, personal_repo, cache)

    @pytest.fixture
    def sample_task(self) -> Task:
        return Task(
            id=TaskId.generate(),
            title="Test task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_TEAM,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_get_task_from_cache(self, service, cache, sample_task):
        """Should get task from cache if present."""
        await cache.set(sample_task.id.value, sample_task)

        result = await service.get_task(sample_task.id)
        assert result == sample_task

    @pytest.mark.asyncio
    async def test_get_task_from_team_repo(self, service, team_repo, cache, sample_task):
        """Should get task from team repo and cache it."""
        await team_repo.create(sample_task)

        result = await service.get_task(sample_task.id)

        assert result == sample_task
        # Should be cached now
        cached = await cache.get(sample_task.id.value)
        assert cached == sample_task

    @pytest.mark.asyncio
    async def test_get_task_from_personal_repo(self, service, personal_repo, cache):
        """Should get task from personal repo if not in team repo."""
        task = Task(
            id=TaskId.generate(),
            title="Personal task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_PERSONAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await personal_repo.create(task)

        result = await service.get_task(task.id)

        assert result == task
        # Should be cached now
        cached = await cache.get(task.id.value)
        assert cached == task

    @pytest.mark.asyncio
    async def test_get_task_returns_none_if_not_found(self, service):
        """Should return None if task not found anywhere."""
        result = await service.get_task(TaskId.generate())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_tasks_from_cache(self, service, cache):
        """Should list tasks from cache."""
        tasks = [
            Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(3)
        ]
        for task in tasks:
            await cache.set(task.id.value, task)

        result = await service.list_tasks()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self, service, cache):
        """Should filter tasks by status."""
        todo_task = Task(
            id=TaskId.generate(),
            title="Todo",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        done_task = Task(
            id=TaskId.generate(),
            title="Done",
            status=TaskStatus.DONE,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(todo_task.id.value, todo_task)
        await cache.set(done_task.id.value, done_task)

        result = await service.list_tasks(TaskFilter(status=[TaskStatus.TODO]))

        assert len(result) == 1
        assert result[0].title == "Todo"

    @pytest.mark.asyncio
    async def test_list_tasks_with_priority_filter(self, service, cache):
        """Should filter tasks by priority."""
        high_task = Task(
            id=TaskId.generate(),
            title="High priority",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        low_task = Task(
            id=TaskId.generate(),
            title="Low priority",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            priority=TaskPriority.LOW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(high_task.id.value, high_task)
        await cache.set(low_task.id.value, low_task)

        result = await service.list_tasks(TaskFilter(priority=[TaskPriority.HIGH]))

        assert len(result) == 1
        assert result[0].title == "High priority"

    @pytest.mark.asyncio
    async def test_create_task_in_team_repo(self, service, team_repo, cache, sample_task):
        """Should create task in team repo and cache it."""
        created = await service.create_task(sample_task, personal=False)

        assert await team_repo.exists(sample_task.id)
        assert await cache.get(sample_task.id.value) == created

    @pytest.mark.asyncio
    async def test_create_task_in_personal_repo(self, service, personal_repo, cache):
        """Should create task in personal repo when specified."""
        task = Task(
            id=TaskId.generate(),
            title="Personal task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_PERSONAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created = await service.create_task(task, personal=True)

        assert await personal_repo.exists(task.id)
        assert await cache.get(task.id.value) == created

    @pytest.mark.asyncio
    async def test_update_task_in_team_repo(self, service, team_repo, cache, sample_task):
        """Should update task in team repo and refresh cache."""
        await team_repo.create(sample_task)
        await cache.set(sample_task.id.value, sample_task)

        updated_task = replace(sample_task, title="Updated title")
        result = await service.update_task(updated_task)

        assert result.title == "Updated title"
        cached = await cache.get(sample_task.id.value)
        assert cached.title == "Updated title"

    @pytest.mark.asyncio
    async def test_update_task_in_personal_repo(self, service, personal_repo, cache):
        """Should update task in personal repo."""
        task = Task(
            id=TaskId.generate(),
            title="Personal task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_PERSONAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await personal_repo.create(task)

        updated_task = replace(task, title="Updated personal")
        result = await service.update_task(updated_task)

        assert result.title == "Updated personal"

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_raises_error(self, service, sample_task):
        """Should raise error when updating nonexistent task."""
        with pytest.raises(ValueError, match="not found"):
            await service.update_task(sample_task)

    @pytest.mark.asyncio
    async def test_update_task_status(self, service, team_repo, cache, sample_task):
        """Should update task status."""
        await team_repo.create(sample_task)
        await cache.set(sample_task.id.value, sample_task)

        result = await service.update_task_status(sample_task.id, TaskStatus.DONE)

        assert result.status == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_update_task_status_not_found(self, service):
        """Should raise error when task not found."""
        with pytest.raises(ValueError, match="not found"):
            await service.update_task_status(TaskId.generate(), TaskStatus.DONE)

    @pytest.mark.asyncio
    async def test_delete_task_from_team_repo(self, service, team_repo, cache, sample_task):
        """Should delete task from team repo and cache."""
        await team_repo.create(sample_task)
        await cache.set(sample_task.id.value, sample_task)

        result = await service.delete_task(sample_task.id)

        assert result is True
        assert await team_repo.exists(sample_task.id) is False
        assert await cache.get(sample_task.id.value) is None

    @pytest.mark.asyncio
    async def test_delete_task_from_personal_repo(self, service, personal_repo, cache):
        """Should delete task from personal repo."""
        task = Task(
            id=TaskId.generate(),
            title="Personal task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_PERSONAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await personal_repo.create(task)
        await cache.set(task.id.value, task)

        result = await service.delete_task(task.id)

        assert result is True
        assert await personal_repo.exists(task.id) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, service):
        """Should return False when deleting nonexistent task."""
        result = await service.delete_task(TaskId.generate())
        assert result is False

    @pytest.mark.asyncio
    async def test_sync_from_team(self, service, team_repo, cache):
        """Should sync tasks from team repo to cache."""
        tasks = [
            Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.NOTION_TEAM,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(3)
        ]
        for task in tasks:
            await team_repo.create(task)

        count = await service.sync_from_team()

        assert count == 3
        cached = await cache.get_all()
        assert len(cached) == 3

    @pytest.mark.asyncio
    async def test_sync_from_personal(self, service, personal_repo, cache):
        """Should sync tasks from personal repo to cache."""
        tasks = [
            Task(
                id=TaskId.generate(),
                title=f"Personal task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.NOTION_PERSONAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(2)
        ]
        for task in tasks:
            await personal_repo.create(task)

        count = await service.sync_from_personal()

        assert count == 2

    @pytest.mark.asyncio
    async def test_sync_all(self, service, team_repo, personal_repo, cache):
        """Should sync tasks from both repositories."""
        team_task = Task(
            id=TaskId.generate(),
            title="Team task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_TEAM,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        personal_task = Task(
            id=TaskId.generate(),
            title="Personal task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_PERSONAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await team_repo.create(team_task)
        await personal_repo.create(personal_task)

        result = await service.sync_all()

        assert result["team_tasks"] == 1
        assert result["personal_tasks"] == 1

    @pytest.mark.asyncio
    async def test_get_tasks_due_today(self, service, cache):
        """Should get tasks due today."""
        due_today = Task(
            id=TaskId.generate(),
            title="Due today",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        due_tomorrow = Task(
            id=TaskId.generate(),
            title="Due tomorrow",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() + timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(due_today.id.value, due_today)
        await cache.set(due_tomorrow.id.value, due_tomorrow)

        result = await service.get_tasks_due_today()

        assert len(result) == 1
        assert result[0].title == "Due today"

    @pytest.mark.asyncio
    async def test_get_overdue_tasks(self, service, cache):
        """Should get overdue tasks."""
        overdue = Task(
            id=TaskId.generate(),
            title="Overdue",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() - timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        not_overdue = Task(
            id=TaskId.generate(),
            title="Not overdue",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() + timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        done_overdue = Task(
            id=TaskId.generate(),
            title="Done overdue",
            status=TaskStatus.DONE,
            source=TaskSource.MANUAL,
            due_date=datetime.now() - timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await cache.set(overdue.id.value, overdue)
        await cache.set(not_overdue.id.value, not_overdue)
        await cache.set(done_overdue.id.value, done_overdue)

        result = await service.get_overdue_tasks()

        assert len(result) == 1
        assert result[0].title == "Overdue"
