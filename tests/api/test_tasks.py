"""Tests for task endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.container import get_container, reset_container
from src.repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository
from src.domain.models import Task, TaskId, TaskStatus, TaskPriority, TaskSource


@pytest.fixture(autouse=True)
def setup_container():
    """Set up container with in-memory repositories for testing."""
    reset_container()
    container = get_container()
    container.configure_task_repository(InMemoryTaskRepository)
    container.configure_personal_task_repository(InMemoryTaskRepository)
    container.configure_cache_repository(InMemoryCacheRepository)
    yield
    reset_container()


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_task():
    """Create sample task."""
    return Task(
        id=TaskId.generate(),
        title="Test Task",
        description="Test description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        source=TaskSource.MANUAL,
        tags=["test"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class TestListTasks:
    """Tests for list tasks endpoint."""

    def test_list_empty(self, client):
        """Should return empty list when no tasks."""
        response = client.get("/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_list_tasks(self, client, sample_task):
        """Should return all tasks."""
        # Add task to cache
        container = get_container()
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        response = client.get("/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Test Task"

    def test_filter_by_status(self, client, sample_task):
        """Should filter by status."""
        container = get_container()
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        # Filter for TODO
        response = client.get("/tasks?status=todo")
        assert response.status_code == 200
        assert len(response.json()["tasks"]) == 1

        # Filter for DONE
        response = client.get("/tasks?status=done")
        assert response.status_code == 200
        assert len(response.json()["tasks"]) == 0

    def test_filter_invalid_status(self, client):
        """Should return 400 for invalid status."""
        response = client.get("/tasks?status=invalid")

        assert response.status_code == 400

    def test_filter_by_priority(self, client, sample_task):
        """Should filter by priority."""
        container = get_container()
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        # Filter for MEDIUM
        response = client.get("/tasks?priority=medium")
        assert response.status_code == 200
        assert len(response.json()["tasks"]) == 1

        # Filter for HIGH
        response = client.get("/tasks?priority=high")
        assert response.status_code == 200
        assert len(response.json()["tasks"]) == 0


class TestGetTask:
    """Tests for get task endpoint."""

    def test_get_existing_task(self, client, sample_task):
        """Should return task by ID."""
        container = get_container()
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        response = client.get(f"/tasks/{sample_task.id.value}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_task.id.value
        assert data["title"] == "Test Task"

    def test_get_nonexistent_task(self, client):
        """Should return 404 for nonexistent task."""
        response = client.get("/tasks/nonexistent-id")

        assert response.status_code == 404


class TestCreateTask:
    """Tests for create task endpoint."""

    def test_create_minimal_task(self, client):
        """Should create task with minimal data."""
        response = client.post("/tasks", json={
            "title": "New Task",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["status"] == "todo"
        assert data["priority"] == "medium"

    def test_create_full_task(self, client):
        """Should create task with all fields."""
        response = client.post("/tasks", json={
            "title": "Full Task",
            "description": "Task description",
            "priority": "high",
            "due_date": "2024-01-15T14:00:00",
            "tags": ["feature", "urgent"],
            "personal": True,
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Full Task"
        assert data["description"] == "Task description"
        assert data["priority"] == "high"
        assert data["source"] == "notion_personal"
        assert "feature" in data["tags"]

    def test_create_task_invalid_priority(self, client):
        """Should return 400 for invalid priority."""
        response = client.post("/tasks", json={
            "title": "Task",
            "priority": "invalid",
        })

        assert response.status_code == 400


class TestUpdateTask:
    """Tests for update task endpoint."""

    def test_update_task_title(self, client, sample_task):
        """Should update task title."""
        container = get_container()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )
        loop.run_until_complete(
            container.task_repository.create(sample_task)
        )

        response = client.patch(f"/tasks/{sample_task.id.value}", json={
            "title": "Updated Title",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_task_status(self, client, sample_task):
        """Should update task status."""
        container = get_container()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )
        loop.run_until_complete(
            container.task_repository.create(sample_task)
        )

        response = client.patch(f"/tasks/{sample_task.id.value}", json={
            "status": "in_progress",
        })

        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_nonexistent_task(self, client):
        """Should return 404 for nonexistent task."""
        response = client.patch("/tasks/nonexistent", json={
            "title": "Updated",
        })

        assert response.status_code == 404


class TestUpdateTaskStatus:
    """Tests for update task status endpoint."""

    def test_update_status_to_done(self, client, sample_task):
        """Should update status to done."""
        container = get_container()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )
        loop.run_until_complete(
            container.task_repository.create(sample_task)
        )

        response = client.patch(
            f"/tasks/{sample_task.id.value}/status?status=done"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_update_status_invalid(self, client, sample_task):
        """Should return 400 for invalid status."""
        container = get_container()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )

        response = client.patch(
            f"/tasks/{sample_task.id.value}/status?status=invalid"
        )

        assert response.status_code == 400


class TestDeleteTask:
    """Tests for delete task endpoint."""

    def test_delete_existing_task(self, client, sample_task):
        """Should delete existing task."""
        container = get_container()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            container.cache_repository.set(sample_task.id.value, sample_task)
        )
        loop.run_until_complete(
            container.task_repository.create(sample_task)
        )

        response = client.delete(f"/tasks/{sample_task.id.value}")

        assert response.status_code == 204

    def test_delete_nonexistent_task(self, client):
        """Should return 404 for nonexistent task."""
        response = client.delete("/tasks/nonexistent")

        assert response.status_code == 404


class TestSyncTasks:
    """Tests for sync tasks endpoint."""

    def test_sync_tasks(self, client):
        """Should sync tasks from repositories."""
        response = client.post("/tasks/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "team_tasks" in data
        assert "personal_tasks" in data


class TestDueTodayTasks:
    """Tests for due today tasks endpoint."""

    def test_get_tasks_due_today(self, client):
        """Should return tasks due today."""
        container = get_container()
        import asyncio

        # Create task due today
        task = Task(
            id=TaskId.generate(),
            title="Due Today",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(task.id.value, task)
        )

        response = client.get("/tasks/due/today")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Due Today"


class TestOverdueTasks:
    """Tests for overdue tasks endpoint."""

    def test_get_overdue_tasks(self, client):
        """Should return overdue tasks."""
        container = get_container()
        import asyncio

        # Create overdue task
        task = Task(
            id=TaskId.generate(),
            title="Overdue Task",
            status=TaskStatus.TODO,
            source=TaskSource.MANUAL,
            due_date=datetime.now() - timedelta(days=1),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        asyncio.get_event_loop().run_until_complete(
            container.cache_repository.set(task.id.value, task)
        )

        response = client.get("/tasks/overdue")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Overdue Task"


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Should return healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
