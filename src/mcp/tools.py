"""MCP tools for Claude Code integration."""

from datetime import datetime
from typing import Optional, Any
from dataclasses import asdict

from ..domain.models import (
    Task,
    TaskId,
    TaskStatus,
    TaskPriority,
    TaskSource,
    TaskFilter,
)
from ..services.task_service import TaskService
from ..container import get_container


class MCPTools:
    """Tools for MCP server to interact with task management system."""

    def __init__(self, task_service: Optional[TaskService] = None):
        """Initialize MCP tools.

        Args:
            task_service: Optional TaskService (uses container if not provided)
        """
        self._task_service = task_service

    @property
    def task_service(self) -> TaskService:
        """Get task service."""
        if self._task_service:
            return self._task_service
        return get_container().task_service

    def _task_to_dict(self, task: Task) -> dict:
        """Convert Task to dictionary for MCP response."""
        return {
            "id": task.id.value,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "source": task.source.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "tags": task.tags,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    async def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100,
    ) -> dict:
        """List tasks with optional filters.

        Args:
            status: Filter by status (todo, in_progress, done, blocked)
            priority: Filter by priority (low, medium, high, urgent)
            tags: Filter by tags
            limit: Maximum number of tasks to return

        Returns:
            Dict with tasks list and count
        """
        filter_kwargs = {"limit": limit}

        if status:
            try:
                filter_kwargs["status"] = [TaskStatus(status)]
            except ValueError:
                return {"error": f"Invalid status: {status}"}

        if priority:
            try:
                filter_kwargs["priority"] = [TaskPriority(priority)]
            except ValueError:
                return {"error": f"Invalid priority: {priority}"}

        if tags:
            filter_kwargs["tags"] = tags

        task_filter = TaskFilter(**filter_kwargs)
        tasks = await self.task_service.list_tasks(task_filter)

        return {
            "tasks": [self._task_to_dict(t) for t in tasks],
            "total": len(tasks),
        }

    async def get_task(self, task_id: str) -> dict:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task dict or error message
        """
        task = await self.task_service.get_task(TaskId(task_id))

        if not task:
            return {"error": f"Task not found: {task_id}"}

        return {"task": self._task_to_dict(task)}

    async def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        personal: bool = False,
    ) -> dict:
        """Create a new task.

        Args:
            title: Task title
            description: Task description
            priority: Task priority (low, medium, high, urgent)
            due_date: Due date in ISO format
            tags: List of tags
            personal: True for personal, False for team

        Returns:
            Created task dict or error message
        """
        try:
            task_priority = TaskPriority(priority)
        except ValueError:
            return {"error": f"Invalid priority: {priority}"}

        parsed_due_date = None
        if due_date:
            try:
                parsed_due_date = datetime.fromisoformat(due_date)
            except ValueError:
                return {"error": f"Invalid due date format: {due_date}"}

        source = TaskSource.NOTION_PERSONAL if personal else TaskSource.NOTION_TEAM

        task = Task(
            id=TaskId.generate(),
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=task_priority,
            source=source,
            due_date=parsed_due_date,
            tags=tags or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created = await self.task_service.create_task(task, personal=personal)

        return {"task": self._task_to_dict(created)}

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> dict:
        """Update task status.

        Args:
            task_id: Task ID
            status: New status (todo, in_progress, done, blocked)

        Returns:
            Updated task dict or error message
        """
        try:
            task_status = TaskStatus(status)
        except ValueError:
            return {"error": f"Invalid status: {status}"}

        try:
            task = await self.task_service.update_task_status(
                TaskId(task_id), task_status
            )
            return {"task": self._task_to_dict(task)}
        except ValueError as e:
            return {"error": str(e)}

    async def complete_task(self, task_id: str) -> dict:
        """Mark a task as complete.

        Args:
            task_id: Task ID

        Returns:
            Updated task dict or error message
        """
        return await self.update_task_status(task_id, "done")

    async def get_tasks_due_today(self) -> dict:
        """Get tasks due today.

        Returns:
            Dict with tasks list and count
        """
        tasks = await self.task_service.get_tasks_due_today()

        return {
            "tasks": [self._task_to_dict(t) for t in tasks],
            "total": len(tasks),
            "message": f"You have {len(tasks)} task(s) due today.",
        }

    async def get_overdue_tasks(self) -> dict:
        """Get overdue tasks.

        Returns:
            Dict with tasks list and count
        """
        tasks = await self.task_service.get_overdue_tasks()

        return {
            "tasks": [self._task_to_dict(t) for t in tasks],
            "total": len(tasks),
            "message": f"You have {len(tasks)} overdue task(s).",
        }

    async def sync_tasks(self) -> dict:
        """Sync tasks from all sources.

        Returns:
            Sync result with counts
        """
        result = await self.task_service.sync_all()

        return {
            "status": "success",
            "team_tasks_synced": result["team_tasks"],
            "personal_tasks_synced": result["personal_tasks"],
            "message": f"Synced {result['team_tasks']} team tasks and {result['personal_tasks']} personal tasks.",
        }

    async def delete_task(self, task_id: str) -> dict:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            Success status or error message
        """
        deleted = await self.task_service.delete_task(TaskId(task_id))

        if not deleted:
            return {"error": f"Task not found: {task_id}"}

        return {"status": "success", "message": f"Task {task_id} deleted."}

    async def get_summary(self) -> dict:
        """Get a summary of all tasks.

        Returns:
            Summary with counts by status and priority
        """
        tasks = await self.task_service.list_tasks()

        # Count by status
        status_counts = {}
        for status in TaskStatus:
            count = sum(1 for t in tasks if t.status == status)
            status_counts[status.value] = count

        # Count by priority
        priority_counts = {}
        for priority in TaskPriority:
            count = sum(1 for t in tasks if t.priority == priority)
            priority_counts[priority.value] = count

        # Due today and overdue
        due_today = sum(1 for t in tasks if t.is_due_today() and t.status != TaskStatus.DONE)
        overdue = sum(1 for t in tasks if t.is_overdue())

        return {
            "total_tasks": len(tasks),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "due_today": due_today,
            "overdue": overdue,
            "message": self._build_summary_message(status_counts, due_today, overdue),
        }

    def _build_summary_message(
        self,
        status_counts: dict,
        due_today: int,
        overdue: int,
    ) -> str:
        """Build human-readable summary message."""
        parts = []

        todo = status_counts.get("todo", 0)
        in_progress = status_counts.get("in_progress", 0)

        if todo > 0:
            parts.append(f"{todo}件のTODO")
        if in_progress > 0:
            parts.append(f"{in_progress}件が進行中")
        if due_today > 0:
            parts.append(f"{due_today}件が今日期限")
        if overdue > 0:
            parts.append(f"{overdue}件が期限切れ")

        if not parts:
            return "タスクはありません。"

        return "、".join(parts) + "があります。"

    def get_tool_definitions(self) -> list[dict]:
        """Get MCP tool definitions for registration.

        Returns:
            List of tool definition dicts
        """
        return [
            {
                "name": "list_tasks",
                "description": "タスク一覧を取得します。ステータス、優先度、タグでフィルタリングできます。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["todo", "in_progress", "done", "blocked"],
                            "description": "ステータスでフィルタ",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "優先度でフィルタ",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "タグでフィルタ",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "最大取得件数",
                            "default": 100,
                        },
                    },
                },
            },
            {
                "name": "get_task",
                "description": "指定IDのタスクを取得します。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "タスクID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "create_task",
                "description": "新しいタスクを作成します。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "タスクタイトル",
                        },
                        "description": {
                            "type": "string",
                            "description": "タスクの説明",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "優先度",
                            "default": "medium",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "期限 (ISO形式: 2024-01-15T14:00:00)",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "タグ",
                        },
                        "personal": {
                            "type": "boolean",
                            "description": "個人用タスクかどうか",
                            "default": False,
                        },
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "update_task_status",
                "description": "タスクのステータスを更新します。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "タスクID",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["todo", "in_progress", "done", "blocked"],
                            "description": "新しいステータス",
                        },
                    },
                    "required": ["task_id", "status"],
                },
            },
            {
                "name": "complete_task",
                "description": "タスクを完了にします。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "タスクID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "get_tasks_due_today",
                "description": "今日が期限のタスクを取得します。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_overdue_tasks",
                "description": "期限切れのタスクを取得します。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "sync_tasks",
                "description": "Notionからタスクを同期します。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "delete_task",
                "description": "タスクを削除します。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "タスクID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "get_summary",
                "description": "タスクのサマリーを取得します。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
