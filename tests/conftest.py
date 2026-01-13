"""Shared pytest fixtures."""

import pytest
from datetime import datetime

from src.domain.models import Task, TaskId, TaskStatus, TaskSource, TaskPriority


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id=TaskId.generate(),
        title="Test task",
        status=TaskStatus.TODO,
        source=TaskSource.MANUAL,
        priority=TaskPriority.MEDIUM,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_task_with_due_date() -> Task:
    """Create a sample task with a due date."""
    return Task(
        id=TaskId.generate(),
        title="Task with due date",
        status=TaskStatus.TODO,
        source=TaskSource.NOTION_TEAM,
        priority=TaskPriority.HIGH,
        due_date=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
