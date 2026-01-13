"""Tests for MCP tools."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.mcp.tools import MCPTools
from src.domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskPriority,
    TaskSource,
)


class TestMCPTools:
    """Tests for MCPTools."""

    @pytest.fixture
    def mock_task_service(self):
        """Create mock task service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def tools(self, mock_task_service):
        """Create MCPTools with mock service."""
        return MCPTools(task_service=mock_task_service)

    @pytest.fixture
    def sample_task(self):
        """Create sample task."""
        return Task(
            id=TaskId("test-123"),
            title="Test Task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            source=TaskSource.MANUAL,
            tags=["test"],
            created_at=datetime(2024, 1, 1, 10, 0),
            updated_at=datetime(2024, 1, 1, 10, 0),
        )

    @pytest.mark.asyncio
    async def test_list_tasks(self, tools, mock_task_service, sample_task):
        """Should list tasks."""
        mock_task_service.list_tasks.return_value = [sample_task]

        result = await tools.list_tasks()

        assert result["total"] == 1
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Test Task"

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self, tools, mock_task_service, sample_task):
        """Should filter by status."""
        mock_task_service.list_tasks.return_value = [sample_task]

        result = await tools.list_tasks(status="todo")

        assert result["total"] == 1
        mock_task_service.list_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_invalid_status(self, tools, mock_task_service):
        """Should return error for invalid status."""
        result = await tools.list_tasks(status="invalid")

        assert "error" in result
        assert "Invalid status" in result["error"]

    @pytest.mark.asyncio
    async def test_list_tasks_with_priority_filter(self, tools, mock_task_service, sample_task):
        """Should filter by priority."""
        mock_task_service.list_tasks.return_value = [sample_task]

        result = await tools.list_tasks(priority="high")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_task_found(self, tools, mock_task_service, sample_task):
        """Should return task when found."""
        mock_task_service.get_task.return_value = sample_task

        result = await tools.get_task("test-123")

        assert "task" in result
        assert result["task"]["id"] == "test-123"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, tools, mock_task_service):
        """Should return error when not found."""
        mock_task_service.get_task.return_value = None

        result = await tools.get_task("nonexistent")

        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_create_task(self, tools, mock_task_service, sample_task):
        """Should create task."""
        mock_task_service.create_task.return_value = sample_task

        result = await tools.create_task(
            title="New Task",
            description="Description",
            priority="high",
            tags=["feature"],
        )

        assert "task" in result
        mock_task_service.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_due_date(self, tools, mock_task_service, sample_task):
        """Should create task with due date."""
        mock_task_service.create_task.return_value = sample_task

        result = await tools.create_task(
            title="New Task",
            due_date="2024-01-15T14:00:00",
        )

        assert "task" in result

    @pytest.mark.asyncio
    async def test_create_task_invalid_due_date(self, tools, mock_task_service):
        """Should return error for invalid due date."""
        result = await tools.create_task(
            title="New Task",
            due_date="invalid-date",
        )

        assert "error" in result
        assert "Invalid due date" in result["error"]

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(self, tools, mock_task_service):
        """Should return error for invalid priority."""
        result = await tools.create_task(
            title="New Task",
            priority="invalid",
        )

        assert "error" in result
        assert "Invalid priority" in result["error"]

    @pytest.mark.asyncio
    async def test_update_task_status(self, tools, mock_task_service, sample_task):
        """Should update task status."""
        updated_task = Task(
            id=sample_task.id,
            title=sample_task.title,
            description=sample_task.description,
            status=TaskStatus.DONE,
            priority=sample_task.priority,
            source=sample_task.source,
            tags=sample_task.tags,
            created_at=sample_task.created_at,
            updated_at=datetime.now(),
        )
        mock_task_service.update_task_status.return_value = updated_task

        result = await tools.update_task_status("test-123", "done")

        assert "task" in result
        assert result["task"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_update_task_status_invalid(self, tools, mock_task_service):
        """Should return error for invalid status."""
        result = await tools.update_task_status("test-123", "invalid")

        assert "error" in result
        assert "Invalid status" in result["error"]

    @pytest.mark.asyncio
    async def test_update_task_status_not_found(self, tools, mock_task_service):
        """Should return error when task not found."""
        mock_task_service.update_task_status.side_effect = ValueError("Task not found")

        result = await tools.update_task_status("nonexistent", "done")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_complete_task(self, tools, mock_task_service, sample_task):
        """Should complete task."""
        completed_task = Task(
            id=sample_task.id,
            title=sample_task.title,
            description=sample_task.description,
            status=TaskStatus.DONE,
            priority=sample_task.priority,
            source=sample_task.source,
            tags=sample_task.tags,
            created_at=sample_task.created_at,
            updated_at=datetime.now(),
        )
        mock_task_service.update_task_status.return_value = completed_task

        result = await tools.complete_task("test-123")

        assert "task" in result
        assert result["task"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_get_tasks_due_today(self, tools, mock_task_service, sample_task):
        """Should get tasks due today."""
        mock_task_service.get_tasks_due_today.return_value = [sample_task]

        result = await tools.get_tasks_due_today()

        assert result["total"] == 1
        assert "message" in result

    @pytest.mark.asyncio
    async def test_get_overdue_tasks(self, tools, mock_task_service, sample_task):
        """Should get overdue tasks."""
        mock_task_service.get_overdue_tasks.return_value = [sample_task]

        result = await tools.get_overdue_tasks()

        assert result["total"] == 1
        assert "message" in result

    @pytest.mark.asyncio
    async def test_sync_tasks(self, tools, mock_task_service):
        """Should sync tasks."""
        mock_task_service.sync_all.return_value = {
            "team_tasks": 5,
            "personal_tasks": 3,
        }

        result = await tools.sync_tasks()

        assert result["status"] == "success"
        assert result["team_tasks_synced"] == 5
        assert result["personal_tasks_synced"] == 3

    @pytest.mark.asyncio
    async def test_delete_task_success(self, tools, mock_task_service):
        """Should delete task."""
        mock_task_service.delete_task.return_value = True

        result = await tools.delete_task("test-123")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, tools, mock_task_service):
        """Should return error when task not found."""
        mock_task_service.delete_task.return_value = False

        result = await tools.delete_task("nonexistent")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_summary(self, tools, mock_task_service):
        """Should get task summary."""
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
                title="In Progress Task",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.MEDIUM,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id=TaskId.generate(),
                title="Done Task",
                status=TaskStatus.DONE,
                priority=TaskPriority.LOW,
                source=TaskSource.MANUAL,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_task_service.list_tasks.return_value = tasks

        result = await tools.get_summary()

        assert result["total_tasks"] == 3
        assert result["by_status"]["todo"] == 1
        assert result["by_status"]["in_progress"] == 1
        assert result["by_status"]["done"] == 1
        assert "message" in result

    def test_get_tool_definitions(self, tools):
        """Should return tool definitions."""
        definitions = tools.get_tool_definitions()

        assert len(definitions) > 0

        # Check required tools exist
        tool_names = [d["name"] for d in definitions]
        assert "list_tasks" in tool_names
        assert "get_task" in tool_names
        assert "create_task" in tool_names
        assert "update_task_status" in tool_names
        assert "complete_task" in tool_names
        assert "sync_tasks" in tool_names

    def test_tool_definitions_have_required_fields(self, tools):
        """Should have required fields in definitions."""
        definitions = tools.get_tool_definitions()

        for definition in definitions:
            assert "name" in definition
            assert "description" in definition
            assert "parameters" in definition

    def test_build_summary_message_with_tasks(self, tools):
        """Should build summary message."""
        status_counts = {
            "todo": 3,
            "in_progress": 2,
        }

        message = tools._build_summary_message(status_counts, 1, 2)

        assert "3件のTODO" in message
        assert "2件が進行中" in message
        assert "1件が今日期限" in message
        assert "2件が期限切れ" in message

    def test_build_summary_message_empty(self, tools):
        """Should build message for no tasks."""
        status_counts = {}

        message = tools._build_summary_message(status_counts, 0, 0)

        assert "タスクはありません" in message
