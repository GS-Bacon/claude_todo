"""Tests for in-memory repositories."""

import pytest
from datetime import datetime, timedelta

from src.domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskSource,
    TaskPriority,
    TaskFilter,
)
from src.repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository


class TestInMemoryTaskRepository:
    """Tests for InMemoryTaskRepository."""

    @pytest.fixture
    def repository(self) -> InMemoryTaskRepository:
        """Create a fresh repository for each test."""
        return InMemoryTaskRepository()

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task."""
        return Task(
            id=TaskId.generate(),
            title="Test task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_create_and_get(self, repository, sample_task):
        """Should create and retrieve a task."""
        created = await repository.create(sample_task)
        retrieved = await repository.get_by_id(sample_task.id)
        assert retrieved == created
        assert retrieved.title == "Test task"

    @pytest.mark.asyncio
    async def test_create_duplicate_raises_error(self, repository, sample_task):
        """Should raise error when creating duplicate task."""
        await repository.create(sample_task)
        with pytest.raises(ValueError, match="already exists"):
            await repository.create(sample_task)

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repository):
        """Should return None for nonexistent task."""
        result = await repository.get_by_id(TaskId.generate())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, repository):
        """Should return empty list when no tasks."""
        tasks = await repository.list_tasks()
        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_tasks_returns_all(self, repository):
        """Should return all tasks when no filter."""
        for i in range(3):
            task = Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            await repository.create(task)

        tasks = await repository.list_tasks()
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, repository):
        """Should filter by status."""
        task1 = Task(
            id=TaskId.generate(),
            title="Todo",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        task2 = Task(
            id=TaskId.generate(),
            title="Done",
            status=TaskStatus.DONE,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await repository.create(task1)
        await repository.create(task2)

        filter = TaskFilter(status=[TaskStatus.TODO])
        result = await repository.list_tasks(filter)

        assert len(result) == 1
        assert result[0].title == "Todo"

    @pytest.mark.asyncio
    async def test_list_with_priority_filter(self, repository):
        """Should filter by priority."""
        task1 = Task(
            id=TaskId.generate(),
            title="High priority",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        task2 = Task(
            id=TaskId.generate(),
            title="Low priority",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            priority=TaskPriority.LOW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await repository.create(task1)
        await repository.create(task2)

        filter = TaskFilter(priority=[TaskPriority.HIGH])
        result = await repository.list_tasks(filter)

        assert len(result) == 1
        assert result[0].title == "High priority"

    @pytest.mark.asyncio
    async def test_list_with_source_filter(self, repository):
        """Should filter by source."""
        task1 = Task(
            id=TaskId.generate(),
            title="Slack mention",
            status=TaskStatus.TODO,
            source=TaskSource.SLACK_MENTION,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        task2 = Task(
            id=TaskId.generate(),
            title="Manual task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await repository.create(task1)
        await repository.create(task2)

        filter = TaskFilter(source=[TaskSource.SLACK_MENTION])
        result = await repository.list_tasks(filter)

        assert len(result) == 1
        assert result[0].title == "Slack mention"

    @pytest.mark.asyncio
    async def test_list_with_due_before_filter(self, repository):
        """Should filter by due date (before)."""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        task1 = Task(
            id=TaskId.generate(),
            title="Due today",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=today,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        task2 = Task(
            id=TaskId.generate(),
            title="Due tomorrow",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=tomorrow,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await repository.create(task1)
        await repository.create(task2)

        filter = TaskFilter(due_before=tomorrow)
        result = await repository.list_tasks(filter)

        assert len(result) == 1
        assert result[0].title == "Due today"

    @pytest.mark.asyncio
    async def test_list_with_tags_filter(self, repository):
        """Should filter by tags."""
        task1 = Task(
            id=TaskId.generate(),
            title="Bug fix",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            tags=["bug", "urgent"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        task2 = Task(
            id=TaskId.generate(),
            title="Feature",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            tags=["feature"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await repository.create(task1)
        await repository.create(task2)

        filter = TaskFilter(tags=["bug"])
        result = await repository.list_tasks(filter)

        assert len(result) == 1
        assert result[0].title == "Bug fix"

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, repository):
        """Should apply pagination."""
        for i in range(5):
            task = Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            await repository.create(task)

        filter = TaskFilter(limit=2, offset=1)
        result = await repository.list_tasks(filter)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_update_task(self, repository, sample_task):
        """Should update a task."""
        await repository.create(sample_task)

        # Update the task
        from dataclasses import replace

        updated_task = replace(sample_task, title="Updated title")
        result = await repository.update(updated_task)

        assert result.title == "Updated title"

        # Verify persistence
        retrieved = await repository.get_by_id(sample_task.id)
        assert retrieved.title == "Updated title"

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises_error(self, repository, sample_task):
        """Should raise error when updating nonexistent task."""
        with pytest.raises(ValueError, match="not found"):
            await repository.update(sample_task)

    @pytest.mark.asyncio
    async def test_delete_task(self, repository, sample_task):
        """Should delete a task."""
        await repository.create(sample_task)

        result = await repository.delete(sample_task.id)
        assert result is True

        # Verify deletion
        retrieved = await repository.get_by_id(sample_task.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, repository):
        """Should return False when deleting nonexistent task."""
        result = await repository.delete(TaskId.generate())
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, repository, sample_task):
        """Should return True for existing task."""
        await repository.create(sample_task)
        assert await repository.exists(sample_task.id) is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, repository):
        """Should return False for nonexistent task."""
        assert await repository.exists(TaskId.generate()) is False


class TestInMemoryCacheRepository:
    """Tests for InMemoryCacheRepository."""

    @pytest.fixture
    def cache(self) -> InMemoryCacheRepository:
        """Create a fresh cache for each test."""
        return InMemoryCacheRepository()

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task."""
        return Task(
            id=TaskId.generate(),
            title="Cached task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache, sample_task):
        """Should set and get a cached task."""
        await cache.set(sample_task.id.value, sample_task)
        retrieved = await cache.get(sample_task.id.value)
        assert retrieved == sample_task

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, cache):
        """Should return None for nonexistent key."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_empty(self, cache):
        """Should return empty list when cache is empty."""
        result = await cache.get_all()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_returns_all(self, cache):
        """Should return all cached tasks."""
        tasks = []
        for i in range(3):
            task = Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            tasks.append(task)
            await cache.set(task.id.value, task)

        result = await cache.get_all()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_set_many(self, cache):
        """Should set multiple tasks at once."""
        tasks = {}
        for i in range(3):
            task = Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            tasks[task.id.value] = task

        await cache.set_many(tasks)

        result = await cache.get_all()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_invalidate_existing(self, cache, sample_task):
        """Should invalidate existing cached task."""
        await cache.set(sample_task.id.value, sample_task)

        result = await cache.invalidate(sample_task.id.value)
        assert result is True

        # Verify invalidation
        retrieved = await cache.get(sample_task.id.value)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_returns_false(self, cache):
        """Should return False when invalidating nonexistent key."""
        result = await cache.invalidate("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Should clear all cached tasks."""
        for i in range(3):
            task = Task(
                id=TaskId.generate(),
                title=f"Task {i}",
                status=TaskStatus.TODO,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            await cache.set(task.id.value, task)

        await cache.clear()

        result = await cache.get_all()
        assert result == []
