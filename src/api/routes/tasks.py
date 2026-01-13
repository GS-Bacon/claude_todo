"""Task management routes."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...domain.models import TaskStatus, TaskPriority, TaskFilter
from ...services.task_service import TaskService
from ...container import get_container

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    """Task response model."""

    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    source: str
    due_date: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Task list response model."""

    tasks: list[TaskResponse]
    total: int


class TaskCreateRequest(BaseModel):
    """Task creation request model."""

    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    personal: bool = False


class TaskUpdateRequest(BaseModel):
    """Task update request model."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[list[str]] = None


def get_task_service() -> TaskService:
    """Get TaskService from container."""
    container = get_container()
    return container.task_service


def task_to_response(task) -> TaskResponse:
    """Convert Task to TaskResponse."""
    return TaskResponse(
        id=task.id.value,
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority.value,
        source=task.source.value,
        due_date=task.due_date,
        tags=task.tags,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# Static routes must come before dynamic routes
@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status (todo, in_progress, done, blocked)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, urgent)"),
    due_before: Optional[datetime] = Query(None, description="Filter by due date before"),
    due_after: Optional[datetime] = Query(None, description="Filter by due date after"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> TaskListResponse:
    """List tasks with optional filters."""
    service = get_task_service()

    # Build filter
    filter_kwargs = {"limit": limit, "offset": offset}

    if status:
        try:
            filter_kwargs["status"] = [TaskStatus(status)]
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    if priority:
        try:
            filter_kwargs["priority"] = [TaskPriority(priority)]
        except ValueError:
            raise HTTPException(400, f"Invalid priority: {priority}")

    if due_before:
        filter_kwargs["due_before"] = due_before

    if due_after:
        filter_kwargs["due_after"] = due_after

    if tags:
        filter_kwargs["tags"] = [t.strip() for t in tags.split(",")]

    task_filter = TaskFilter(**filter_kwargs)
    tasks = await service.list_tasks(task_filter)

    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(request: TaskCreateRequest) -> TaskResponse:
    """Create a new task."""
    from ...domain.models import Task, TaskId, TaskSource

    service = get_task_service()

    # Parse priority
    try:
        priority = TaskPriority(request.priority)
    except ValueError:
        raise HTTPException(400, f"Invalid priority: {request.priority}")

    # Determine source based on personal flag
    source = TaskSource.NOTION_PERSONAL if request.personal else TaskSource.NOTION_TEAM

    task = Task(
        id=TaskId.generate(),
        title=request.title,
        description=request.description,
        status=TaskStatus.TODO,
        priority=priority,
        source=source,
        due_date=request.due_date,
        tags=request.tags,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    created = await service.create_task(task, personal=request.personal)
    return task_to_response(created)


@router.post("/sync", response_model=dict)
async def sync_tasks() -> dict:
    """Sync tasks from all sources."""
    service = get_task_service()
    result = await service.sync_all()

    return {
        "status": "success",
        "team_tasks": result["team_tasks"],
        "personal_tasks": result["personal_tasks"],
    }


@router.get("/due/today", response_model=TaskListResponse)
async def get_tasks_due_today() -> TaskListResponse:
    """Get tasks due today."""
    service = get_task_service()
    tasks = await service.get_tasks_due_today()

    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/overdue", response_model=TaskListResponse)
async def get_overdue_tasks() -> TaskListResponse:
    """Get overdue tasks."""
    service = get_task_service()
    tasks = await service.get_overdue_tasks()

    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=len(tasks),
    )


# Dynamic routes must come after static routes
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get task by ID."""
    from ...domain.models import TaskId

    service = get_task_service()
    task = await service.get_task(TaskId(task_id))

    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")

    return task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, request: TaskUpdateRequest) -> TaskResponse:
    """Update an existing task."""
    from dataclasses import replace
    from ...domain.models import TaskId

    service = get_task_service()
    task = await service.get_task(TaskId(task_id))

    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")

    # Build update kwargs
    update_kwargs = {}

    if request.title is not None:
        update_kwargs["title"] = request.title

    if request.description is not None:
        update_kwargs["description"] = request.description

    if request.status is not None:
        try:
            update_kwargs["status"] = TaskStatus(request.status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {request.status}")

    if request.priority is not None:
        try:
            update_kwargs["priority"] = TaskPriority(request.priority)
        except ValueError:
            raise HTTPException(400, f"Invalid priority: {request.priority}")

    if request.due_date is not None:
        update_kwargs["due_date"] = request.due_date

    if request.tags is not None:
        update_kwargs["tags"] = request.tags

    update_kwargs["updated_at"] = datetime.now()

    updated_task = replace(task, **update_kwargs)
    result = await service.update_task(updated_task)

    return task_to_response(result)


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(task_id: str, status: str) -> TaskResponse:
    """Update task status."""
    from ...domain.models import TaskId

    service = get_task_service()

    try:
        task_status = TaskStatus(status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {status}")

    try:
        task = await service.update_task_status(TaskId(task_id), task_status)
        return task_to_response(task)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str) -> None:
    """Delete a task."""
    from ...domain.models import TaskId

    service = get_task_service()
    deleted = await service.delete_task(TaskId(task_id))

    if not deleted:
        raise HTTPException(404, f"Task not found: {task_id}")
