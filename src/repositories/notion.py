"""Notion API repository implementation."""

from datetime import datetime
from typing import Optional, Sequence
import httpx

from ..domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskPriority,
    TaskSource,
    TaskFilter,
)
from ..config.settings import (
    NotionPropertyNames,
    NotionStatusMapping,
    NotionPriorityMapping,
)


class NotionTaskRepository:
    """Repository for managing tasks in Notion database."""

    def __init__(
        self,
        api_key: str,
        database_id: str,
        *,
        source: TaskSource = TaskSource.NOTION_TEAM,
        property_names: Optional[NotionPropertyNames] = None,
        status_mapping: Optional[NotionStatusMapping] = None,
        priority_mapping: Optional[NotionPriorityMapping] = None,
        api_version: str = "2022-06-28",
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize Notion repository.

        Args:
            api_key: Notion API key
            database_id: Notion database ID
            source: Task source type (NOTION_TEAM or NOTION_PERSONAL)
            property_names: Notion property name mappings
            status_mapping: Task status to Notion status value mappings
            priority_mapping: Task priority to Notion priority value mappings
            api_version: Notion API version
            http_client: Optional HTTP client for testing
        """
        self._api_key = api_key
        self._database_id = database_id
        self._source = source
        self._http_client = http_client
        self._owns_client = http_client is None
        self._base_url = "https://api.notion.com/v1"
        self._api_version = api_version

        # Use provided mappings or defaults
        self._props = property_names or NotionPropertyNames()
        self._status_map = status_mapping or NotionStatusMapping()
        self._priority_map = priority_mapping or NotionPriorityMapping()

        # Determine status property type (status or select)
        self._status_type = getattr(self._props, 'status_type', 'status')

        # Build bidirectional mappings
        self._status_to_notion = {
            TaskStatus.TODO: self._status_map.todo,
            TaskStatus.IN_PROGRESS: self._status_map.in_progress,
            TaskStatus.DONE: self._status_map.done,
            TaskStatus.BLOCKED: self._status_map.blocked,
        }
        self._notion_to_status = {v: k for k, v in self._status_to_notion.items()}

        self._priority_to_notion = {
            TaskPriority.LOW: self._priority_map.low,
            TaskPriority.MEDIUM: self._priority_map.medium,
            TaskPriority.HIGH: self._priority_map.high,
            TaskPriority.URGENT: self._priority_map.urgent,
        }
        self._notion_to_priority = {v: k for k, v in self._priority_to_notion.items()}

    def _get_headers(self) -> dict:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Notion-Version": self._api_version,
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._http_client:
            return self._http_client
        return httpx.AsyncClient()

    async def get_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Get task by ID.

        Args:
            task_id: Task ID (must be Notion page ID format)

        Returns:
            Task if found, None otherwise
        """
        # Extract Notion page ID from TaskId
        notion_id = task_id.value
        if notion_id.startswith("notion:"):
            notion_id = notion_id[7:]

        client = await self._get_client()
        try:
            response = await client.get(
                f"{self._base_url}/pages/{notion_id}",
                headers=self._get_headers(),
                timeout=10.0,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            page = response.json()
            return self._page_to_task(page)

        except httpx.HTTPError:
            return None
        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    async def list_tasks(
        self, filter: Optional[TaskFilter] = None
    ) -> Sequence[Task]:
        """List tasks from Notion database.

        Args:
            filter: Optional filter criteria

        Returns:
            Sequence of tasks
        """
        query_filter = self._build_query_filter(filter)
        # Use timestamp sort (works with last_edited_time and created_time properties)
        sorts = [{"timestamp": "last_edited_time", "direction": "descending"}]

        client = await self._get_client()
        try:
            tasks = []
            has_more = True
            start_cursor = None

            while has_more:
                body = {
                    "sorts": sorts,
                }
                # Only include filter if not empty
                if query_filter:
                    body["filter"] = query_filter
                if start_cursor:
                    body["start_cursor"] = start_cursor

                response = await client.post(
                    f"{self._base_url}/databases/{self._database_id}/query",
                    headers=self._get_headers(),
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                for page in data.get("results", []):
                    task = self._page_to_task(page)
                    if task:
                        tasks.append(task)

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

                # Apply limit if specified
                if filter and filter.limit and len(tasks) >= filter.limit:
                    tasks = tasks[: filter.limit]
                    break

            return tasks

        except httpx.HTTPError:
            return []
        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    async def create(self, task: Task) -> Task:
        """Create task in Notion database.

        Args:
            task: Task to create

        Returns:
            Created task with Notion ID
        """
        properties = self._task_to_properties(task)

        client = await self._get_client()
        try:
            response = await client.post(
                f"{self._base_url}/pages",
                headers=self._get_headers(),
                json={
                    "parent": {"database_id": self._database_id},
                    "properties": properties,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            page = response.json()

            # Return task with Notion page ID
            return self._page_to_task(page) or task

        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    async def update(self, task: Task) -> Task:
        """Update task in Notion.

        Args:
            task: Task to update

        Returns:
            Updated task

        Raises:
            ValueError: If task not found
        """
        notion_id = task.external_id or task.id.value
        if notion_id.startswith("notion:"):
            notion_id = notion_id[7:]

        properties = self._task_to_properties(task)

        client = await self._get_client()
        try:
            response = await client.patch(
                f"{self._base_url}/pages/{notion_id}",
                headers=self._get_headers(),
                json={"properties": properties},
                timeout=10.0,
            )

            if response.status_code == 404:
                raise ValueError(f"Task {task.id} not found in Notion")

            response.raise_for_status()
            page = response.json()
            return self._page_to_task(page) or task

        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    async def delete(self, task_id: TaskId) -> bool:
        """Archive task in Notion (soft delete).

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted, False if not found
        """
        notion_id = task_id.value
        if notion_id.startswith("notion:"):
            notion_id = notion_id[7:]

        client = await self._get_client()
        try:
            response = await client.patch(
                f"{self._base_url}/pages/{notion_id}",
                headers=self._get_headers(),
                json={"archived": True},
                timeout=10.0,
            )

            if response.status_code == 404:
                return False

            response.raise_for_status()
            return True

        except httpx.HTTPError:
            return False
        finally:
            if self._owns_client and not self._http_client:
                await client.aclose()

    async def exists(self, task_id: TaskId) -> bool:
        """Check if task exists.

        Args:
            task_id: Task ID to check

        Returns:
            True if exists, False otherwise
        """
        task = await self.get_by_id(task_id)
        return task is not None

    def _build_query_filter(self, filter: Optional[TaskFilter]) -> dict:
        """Build Notion query filter from TaskFilter.

        Args:
            filter: Task filter criteria

        Returns:
            Notion API filter dict
        """
        if not filter:
            return {}

        conditions = []

        # Status filter (supports both "status" and "select" property types)
        if filter.status:
            status_filter_type = self._status_type  # "status" or "select"
            status_conditions = [
                {
                    "property": self._props.status,
                    status_filter_type: {"equals": self._status_to_notion.get(s, self._status_map.todo)},
                }
                for s in filter.status
            ]
            if len(status_conditions) == 1:
                conditions.append(status_conditions[0])
            else:
                conditions.append({"or": status_conditions})

        # Priority filter
        if filter.priority:
            priority_conditions = [
                {
                    "property": self._props.priority,
                    "select": {"equals": self._priority_to_notion.get(p, self._priority_map.medium)},
                }
                for p in filter.priority
            ]
            if len(priority_conditions) == 1:
                conditions.append(priority_conditions[0])
            else:
                conditions.append({"or": priority_conditions})

        # Due date filter
        if filter.due_before:
            conditions.append({
                "property": self._props.due_date,
                "date": {"on_or_before": filter.due_before.isoformat()},
            })

        if filter.due_after:
            conditions.append({
                "property": self._props.due_date,
                "date": {"on_or_after": filter.due_after.isoformat()},
            })

        # Tags filter
        if filter.tags:
            for tag in filter.tags:
                conditions.append({
                    "property": self._props.tags,
                    "multi_select": {"contains": tag},
                })

        # Assignee filter
        if filter.assignee:
            conditions.append({
                "property": self._props.assignee,
                "people": {"contains": filter.assignee},
            })

        if not conditions:
            return {}

        if len(conditions) == 1:
            return conditions[0]

        return {"and": conditions}

    def _task_to_properties(self, task: Task) -> dict:
        """Convert Task to Notion page properties.

        Args:
            task: Task to convert

        Returns:
            Notion properties dict
        """
        # Build status property based on type (status or select)
        status_value = self._status_to_notion.get(task.status, self._status_map.todo)
        if self._status_type == "select":
            status_prop = {"select": {"name": status_value}}
        else:
            status_prop = {"status": {"name": status_value}}

        properties = {
            self._props.title: {"title": [{"text": {"content": task.title}}]},
            self._props.status: status_prop,
            self._props.priority: {"select": {"name": self._priority_to_notion.get(task.priority, self._priority_map.medium)}},
        }

        if task.description and self._props.description:
            properties[self._props.description] = {
                "rich_text": [{"text": {"content": task.description}}]
            }

        if task.due_date and self._props.due_date:
            properties[self._props.due_date] = {"date": {"start": task.due_date.isoformat()}}

        if task.tags and self._props.tags:
            properties[self._props.tags] = {
                "multi_select": [{"name": tag} for tag in task.tags]
            }

        # Store metadata as JSON in a rich_text property (only if property is configured)
        if task.metadata and self._props.metadata:
            import json
            properties[self._props.metadata] = {
                "rich_text": [{"text": {"content": json.dumps(task.metadata)}}]
            }

        return properties

    def _page_to_task(self, page: dict) -> Optional[Task]:
        """Convert Notion page to Task.

        Args:
            page: Notion page response

        Returns:
            Task object or None if conversion fails
        """
        try:
            properties = page.get("properties", {})

            # Extract title
            title_prop = properties.get(self._props.title, {})
            title_content = title_prop.get("title", [])
            title = title_content[0]["text"]["content"] if title_content else "Untitled"

            # Extract status (supports both "status" and "select" property types)
            status_prop = properties.get(self._props.status, {})
            # Try "status" type first, then "select" type
            status_data = status_prop.get("status") or status_prop.get("select")
            status_name = status_data.get("name", self._status_map.todo) if status_data else self._status_map.todo
            status = self._notion_to_status.get(status_name, TaskStatus.TODO)

            # Extract priority
            priority_prop = properties.get(self._props.priority, {})
            priority_select = priority_prop.get("select")
            priority_name = priority_select.get("name", self._priority_map.medium) if priority_select else self._priority_map.medium
            priority = self._notion_to_priority.get(priority_name, TaskPriority.MEDIUM)

            # Extract description
            description_prop = properties.get(self._props.description, {})
            description_content = description_prop.get("rich_text", [])
            description = description_content[0]["text"]["content"] if description_content else None

            # Extract due date
            due_prop = properties.get(self._props.due_date, {})
            due_date_data = due_prop.get("date")
            due_date = None
            if due_date_data and due_date_data.get("start"):
                due_str = due_date_data["start"]
                # Handle both date and datetime formats
                if "T" in due_str:
                    due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                else:
                    due_date = datetime.strptime(due_str, "%Y-%m-%d")

            # Extract tags
            tags_prop = properties.get(self._props.tags, {})
            tags_data = tags_prop.get("multi_select", [])
            tags = [t["name"] for t in tags_data]

            # Extract assignee (supports people, multi_select, and select types)
            assignee = None
            assignees_list = []
            if self._props.assignee:
                assignee_prop = properties.get(self._props.assignee, {})
                # Handle people type
                people_data = assignee_prop.get("people", [])
                if people_data:
                    assignees_list = [p.get("name", "") for p in people_data if p.get("name")]
                    assignee = assignees_list[0] if assignees_list else None
                # Handle multi_select type
                multi_select_data = assignee_prop.get("multi_select", [])
                if multi_select_data:
                    assignees_list = [m["name"] for m in multi_select_data]
                    assignee = assignees_list[0] if assignees_list else None
                # Handle select type
                select_data = assignee_prop.get("select")
                if select_data:
                    assignee = select_data.get("name")
                    assignees_list = [assignee] if assignee else []

            # Extract metadata
            metadata = {}
            metadata_prop = properties.get(self._props.metadata, {})
            metadata_content = metadata_prop.get("rich_text", [])
            if metadata_content:
                import json
                try:
                    metadata = json.loads(metadata_content[0]["text"]["content"])
                except json.JSONDecodeError:
                    pass

            # Store assignees list in metadata for sync service
            if assignees_list:
                metadata["assignees"] = assignees_list

            # Extract timestamps
            created_at = datetime.fromisoformat(
                page.get("created_time", "").replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                page.get("last_edited_time", "").replace("Z", "+00:00")
            )

            return Task(
                id=TaskId.from_notion(page["id"]),
                title=title,
                description=description,
                status=status,
                priority=priority,
                source=self._source,
                due_date=due_date,
                assignee=assignee,
                tags=tags,
                external_id=page["id"],
                metadata=metadata,
                created_at=created_at,
                updated_at=updated_at,
            )

        except (KeyError, IndexError, ValueError):
            return None
