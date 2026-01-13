"""Tests for NotionTaskRepository with mocked HTTP client."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import httpx

from src.repositories.notion import NotionTaskRepository
from src.domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskPriority,
    TaskSource,
    TaskFilter,
)


class TestNotionTaskRepository:
    """Tests for NotionTaskRepository."""

    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def repository(self, mock_client) -> NotionTaskRepository:
        """Create repository with mock client."""
        return NotionTaskRepository(
            api_key="test-api-key",
            database_id="test-database-id",
            source=TaskSource.NOTION_TEAM,
            http_client=mock_client,
        )

    @pytest.fixture
    def sample_notion_page(self) -> dict:
        """Create sample Notion page response."""
        return {
            "id": "page-123",
            "created_time": "2024-01-01T10:00:00.000Z",
            "last_edited_time": "2024-01-02T12:00:00.000Z",
            "properties": {
                "Name": {
                    "title": [{"text": {"content": "Test Task"}}]
                },
                "Status": {
                    "status": {"name": "In progress"}
                },
                "Priority": {
                    "select": {"name": "High"}
                },
                "Description": {
                    "rich_text": [{"text": {"content": "Task description"}}]
                },
                "Due": {
                    "date": {"start": "2024-01-15T14:00:00"}
                },
                "Tags": {
                    "multi_select": [{"name": "bug"}, {"name": "urgent"}]
                },
                "Metadata": {
                    "rich_text": [{"text": {"content": "{\"source_url\": \"https://slack.com/...\"}"}}]
                },
            },
        }

    def test_status_mapping(self, repository):
        """Should correctly map status values."""
        assert repository.STATUS_TO_NOTION[TaskStatus.TODO] == "Not started"
        assert repository.STATUS_TO_NOTION[TaskStatus.IN_PROGRESS] == "In progress"
        assert repository.STATUS_TO_NOTION[TaskStatus.DONE] == "Done"
        assert repository.STATUS_TO_NOTION[TaskStatus.BLOCKED] == "Blocked"

    def test_priority_mapping(self, repository):
        """Should correctly map priority values."""
        assert repository.PRIORITY_TO_NOTION[TaskPriority.LOW] == "Low"
        assert repository.PRIORITY_TO_NOTION[TaskPriority.MEDIUM] == "Medium"
        assert repository.PRIORITY_TO_NOTION[TaskPriority.HIGH] == "High"
        assert repository.PRIORITY_TO_NOTION[TaskPriority.URGENT] == "Urgent"

    def test_page_to_task(self, repository, sample_notion_page):
        """Should convert Notion page to Task."""
        task = repository._page_to_task(sample_notion_page)

        assert task is not None
        assert task.id.value == "notion:page-123"
        assert task.title == "Test Task"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert task.description == "Task description"
        assert task.due_date == datetime(2024, 1, 15, 14, 0)
        assert task.tags == ["bug", "urgent"]
        assert task.metadata.get("source_url") == "https://slack.com/..."

    def test_page_to_task_minimal(self, repository):
        """Should handle minimal Notion page."""
        minimal_page = {
            "id": "page-456",
            "created_time": "2024-01-01T10:00:00.000Z",
            "last_edited_time": "2024-01-01T10:00:00.000Z",
            "properties": {
                "Name": {
                    "title": [{"text": {"content": "Minimal Task"}}]
                },
                "Status": {
                    "status": {"name": "Not started"}
                },
                "Priority": {
                    "select": None
                },
            },
        }

        task = repository._page_to_task(minimal_page)

        assert task is not None
        assert task.title == "Minimal Task"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.MEDIUM
        assert task.description is None
        assert task.due_date is None

    def test_page_to_task_date_only(self, repository):
        """Should handle date-only due dates."""
        page = {
            "id": "page-789",
            "created_time": "2024-01-01T10:00:00.000Z",
            "last_edited_time": "2024-01-01T10:00:00.000Z",
            "properties": {
                "Name": {"title": [{"text": {"content": "Date Task"}}]},
                "Status": {"status": {"name": "Not started"}},
                "Due": {"date": {"start": "2024-01-20"}},
            },
        }

        task = repository._page_to_task(page)

        assert task.due_date == datetime(2024, 1, 20)

    def test_task_to_properties(self, repository):
        """Should convert Task to Notion properties."""
        task = Task(
            id=TaskId.generate(),
            title="New Task",
            description="Task description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            source=TaskSource.NOTION_TEAM,
            due_date=datetime(2024, 1, 15, 14, 0),
            tags=["feature", "review"],
            metadata={"source_url": "https://example.com"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        properties = repository._task_to_properties(task)

        assert properties["Name"]["title"][0]["text"]["content"] == "New Task"
        assert properties["Status"]["status"]["name"] == "In progress"
        assert properties["Priority"]["select"]["name"] == "High"
        assert properties["Description"]["rich_text"][0]["text"]["content"] == "Task description"
        assert properties["Due"]["date"]["start"] is not None
        assert len(properties["Tags"]["multi_select"]) == 2

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_client, sample_notion_page):
        """Should return task when found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_notion_page
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        task = await repository.get_by_id(TaskId("notion:page-123"))

        assert task is not None
        assert task.title == "Test Task"
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_client):
        """Should return None when not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        task = await repository.get_by_id(TaskId("notion:nonexistent"))

        assert task is None

    @pytest.mark.asyncio
    async def test_get_by_id_http_error(self, repository, mock_client):
        """Should return None on HTTP error."""
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        task = await repository.get_by_id(TaskId("notion:page-123"))

        assert task is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, repository, mock_client, sample_notion_page):
        """Should list tasks from database."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [sample_notion_page],
            "has_more": False,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        tasks = await repository.list_tasks()

        assert len(tasks) == 1
        assert tasks[0].title == "Test Task"

    @pytest.mark.asyncio
    async def test_list_tasks_with_pagination(self, repository, mock_client):
        """Should handle pagination."""
        page1 = {
            "id": "page-1",
            "created_time": "2024-01-01T10:00:00.000Z",
            "last_edited_time": "2024-01-01T10:00:00.000Z",
            "properties": {
                "Name": {"title": [{"text": {"content": "Task 1"}}]},
                "Status": {"status": {"name": "Not started"}},
            },
        }
        page2 = {
            "id": "page-2",
            "created_time": "2024-01-01T10:00:00.000Z",
            "last_edited_time": "2024-01-01T10:00:00.000Z",
            "properties": {
                "Name": {"title": [{"text": {"content": "Task 2"}}]},
                "Status": {"status": {"name": "Not started"}},
            },
        }

        response1 = MagicMock()
        response1.status_code = 200
        response1.json.return_value = {
            "results": [page1],
            "has_more": True,
            "next_cursor": "cursor-123",
        }
        response1.raise_for_status = MagicMock()

        response2 = MagicMock()
        response2.status_code = 200
        response2.json.return_value = {
            "results": [page2],
            "has_more": False,
        }
        response2.raise_for_status = MagicMock()

        mock_client.post.side_effect = [response1, response2]

        tasks = await repository.list_tasks()

        assert len(tasks) == 2
        assert tasks[0].title == "Task 1"
        assert tasks[1].title == "Task 2"

    @pytest.mark.asyncio
    async def test_list_tasks_with_filter(self, repository, mock_client):
        """Should build filter query."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "has_more": False}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        filter = TaskFilter(
            status=[TaskStatus.TODO],
            priority=[TaskPriority.HIGH],
        )
        await repository.list_tasks(filter)

        call_args = mock_client.post.call_args
        body = call_args.kwargs["json"]
        assert "filter" in body

    @pytest.mark.asyncio
    async def test_create_task(self, repository, mock_client, sample_notion_page):
        """Should create task in Notion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_notion_page
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        task = Task(
            id=TaskId.generate(),
            title="New Task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_TEAM,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created = await repository.create(task)

        assert created.title == "Test Task"  # From mock response
        assert created.external_id == "page-123"

    @pytest.mark.asyncio
    async def test_update_task(self, repository, mock_client, sample_notion_page):
        """Should update task in Notion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_notion_page
        mock_response.raise_for_status = MagicMock()
        mock_client.patch.return_value = mock_response

        task = Task(
            id=TaskId.from_notion("page-123"),
            title="Updated Task",
            status=TaskStatus.IN_PROGRESS,
            source=TaskSource.NOTION_TEAM,
            external_id="page-123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        updated = await repository.update(task)

        assert updated is not None
        mock_client.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, repository, mock_client):
        """Should raise error when task not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.patch.return_value = mock_response

        task = Task(
            id=TaskId.from_notion("nonexistent"),
            title="Task",
            status=TaskStatus.TODO,
            source=TaskSource.NOTION_TEAM,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with pytest.raises(ValueError, match="not found"):
            await repository.update(task)

    @pytest.mark.asyncio
    async def test_delete_task(self, repository, mock_client):
        """Should archive task in Notion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.patch.return_value = mock_response

        result = await repository.delete(TaskId.from_notion("page-123"))

        assert result is True
        call_args = mock_client.patch.call_args
        body = call_args.kwargs["json"]
        assert body["archived"] is True

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, repository, mock_client):
        """Should return False when task not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.patch.return_value = mock_response

        result = await repository.delete(TaskId.from_notion("nonexistent"))

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_client, sample_notion_page):
        """Should return True when task exists."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_notion_page
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        result = await repository.exists(TaskId.from_notion("page-123"))

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_client):
        """Should return False when task doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        result = await repository.exists(TaskId.from_notion("nonexistent"))

        assert result is False

    def test_build_query_filter_status(self, repository):
        """Should build status filter."""
        filter = TaskFilter(status=[TaskStatus.TODO, TaskStatus.IN_PROGRESS])

        query = repository._build_query_filter(filter)

        assert "or" in query
        assert len(query["or"]) == 2

    def test_build_query_filter_single_status(self, repository):
        """Should build single status filter without or."""
        filter = TaskFilter(status=[TaskStatus.TODO])

        query = repository._build_query_filter(filter)

        assert "property" in query
        assert query["property"] == "Status"

    def test_build_query_filter_combined(self, repository):
        """Should combine multiple filters with and."""
        filter = TaskFilter(
            status=[TaskStatus.TODO],
            priority=[TaskPriority.HIGH],
            tags=["bug"],
        )

        query = repository._build_query_filter(filter)

        assert "and" in query
        assert len(query["and"]) == 3

    def test_build_query_filter_empty(self, repository):
        """Should return empty filter when no criteria."""
        query = repository._build_query_filter(None)
        assert query == {}

        query = repository._build_query_filter(TaskFilter())
        assert query == {}
