"""Task sync service for transferring tasks between databases."""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Callable, Optional, Sequence
import logging

from src.domain.models import Task, TaskId, TaskStatus, TaskPriority, TaskSource
from src.domain.protocols import TaskRepository


logger = logging.getLogger(__name__)


@dataclass
class SyncRule:
    """Rule for syncing tasks from source to destination.

    Attributes:
        name: Human-readable rule name
        source_filter: Function to filter tasks from source (returns True to sync)
        field_mapper: Optional function to transform task before creating in destination
        skip_statuses: Statuses to skip (default: DONE tasks are not synced)
        sync_updates: Whether to sync updates to existing tasks
        enabled: Whether this rule is active
    """

    name: str
    source_filter: Callable[[Task], bool]
    field_mapper: Optional[Callable[[Task], Task]] = None
    skip_statuses: list[TaskStatus] = field(
        default_factory=lambda: [TaskStatus.DONE]
    )
    sync_updates: bool = True
    enabled: bool = True


@dataclass
class SyncResult:
    """Result of a sync operation."""

    rule_name: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class TaskSyncService:
    """Service for syncing tasks between repositories based on rules."""

    # Metadata key to track synced tasks
    SYNC_SOURCE_KEY = "sync_source_id"
    SYNC_SOURCE_DB_KEY = "sync_source_db"

    def __init__(
        self,
        source_repo: TaskRepository,
        dest_repo: TaskRepository,
        source_db_name: str = "team",
        dest_db_name: str = "personal",
    ) -> None:
        """Initialize sync service.

        Args:
            source_repo: Source repository to sync from
            dest_repo: Destination repository to sync to
            source_db_name: Name identifier for source database
            dest_db_name: Name identifier for destination database
        """
        self._source_repo = source_repo
        self._dest_repo = dest_repo
        self._source_db_name = source_db_name
        self._dest_db_name = dest_db_name
        self._rules: list[SyncRule] = []

    def add_rule(self, rule: SyncRule) -> None:
        """Add a sync rule."""
        self._rules.append(rule)
        logger.info(f"Added sync rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a sync rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                self._rules.pop(i)
                logger.info(f"Removed sync rule: {rule_name}")
                return True
        return False

    def list_rules(self) -> list[SyncRule]:
        """List all sync rules."""
        return self._rules.copy()

    async def sync(self, rule_name: Optional[str] = None) -> list[SyncResult]:
        """Execute sync based on rules.

        Args:
            rule_name: If specified, only run this rule. Otherwise run all enabled rules.

        Returns:
            List of sync results for each rule executed
        """
        results = []

        rules_to_run = self._rules
        if rule_name:
            rules_to_run = [r for r in self._rules if r.name == rule_name]

        for rule in rules_to_run:
            if not rule.enabled:
                continue

            result = await self._execute_rule(rule)
            results.append(result)

        return results

    async def _execute_rule(self, rule: SyncRule) -> SyncResult:
        """Execute a single sync rule."""
        result = SyncResult(rule_name=rule.name)

        try:
            # Get all tasks from source
            source_tasks = await self._source_repo.list_tasks()

            # Get existing tasks in destination to check for duplicates
            dest_tasks = await self._dest_repo.list_tasks()
            synced_ids = self._get_synced_source_ids(dest_tasks)

            for task in source_tasks:
                try:
                    # Check if task matches filter
                    if not rule.source_filter(task):
                        continue

                    # Check if status should be skipped
                    if task.status in rule.skip_statuses:
                        result.skipped += 1
                        continue

                    source_id = task.external_id or task.id.value

                    # Check if already synced
                    if source_id in synced_ids:
                        if rule.sync_updates:
                            # Update existing task
                            await self._update_synced_task(
                                task, synced_ids[source_id], rule
                            )
                            result.updated += 1
                        else:
                            result.skipped += 1
                        continue

                    # Create new task in destination
                    await self._create_synced_task(task, rule)
                    result.created += 1

                except Exception as e:
                    error_msg = f"Error syncing task {task.id}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Error executing rule {rule.name}: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        logger.info(
            f"Sync rule '{rule.name}': "
            f"created={result.created}, updated={result.updated}, "
            f"skipped={result.skipped}, errors={len(result.errors)}"
        )

        return result

    def _get_synced_source_ids(
        self, dest_tasks: Sequence[Task]
    ) -> dict[str, Task]:
        """Get mapping of source IDs to destination tasks."""
        synced = {}
        for task in dest_tasks:
            source_id = task.metadata.get(self.SYNC_SOURCE_KEY)
            source_db = task.metadata.get(self.SYNC_SOURCE_DB_KEY)
            if source_id and source_db == self._source_db_name:
                synced[source_id] = task
        return synced

    async def _create_synced_task(self, source_task: Task, rule: SyncRule) -> Task:
        """Create a new task in destination from source task."""
        # Apply field mapper if defined
        task_to_create = source_task
        if rule.field_mapper:
            task_to_create = rule.field_mapper(source_task)

        # Create new task with sync metadata
        source_id = source_task.external_id or source_task.id.value
        new_metadata = {
            **task_to_create.metadata,
            self.SYNC_SOURCE_KEY: source_id,
            self.SYNC_SOURCE_DB_KEY: self._source_db_name,
        }

        new_task = replace(
            task_to_create,
            id=TaskId.generate(),
            source=TaskSource.NOTION_PERSONAL,
            external_id=None,
            metadata=new_metadata,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        return await self._dest_repo.create(new_task)

    async def _update_synced_task(
        self, source_task: Task, dest_task: Task, rule: SyncRule
    ) -> Task:
        """Update existing destination task from source task."""
        # Apply field mapper if defined
        mapped_task = source_task
        if rule.field_mapper:
            mapped_task = rule.field_mapper(source_task)

        # Update destination task with source values
        updated_task = replace(
            dest_task,
            title=mapped_task.title,
            description=mapped_task.description,
            status=mapped_task.status,
            priority=mapped_task.priority,
            due_date=mapped_task.due_date,
            tags=mapped_task.tags,
            updated_at=datetime.now(),
        )

        return await self._dest_repo.update(updated_task)


# Predefined filter functions for common use cases


def assignee_filter(assignee_name: str) -> Callable[[Task], bool]:
    """Create a filter that matches tasks assigned to a specific person.

    Works with both single assignee and multi-select assignee fields.
    """
    def _filter(task: Task) -> bool:
        # Check direct assignee field
        if task.assignee == assignee_name:
            return True

        # Check if assignee is in metadata (for multi-select)
        assignees = task.metadata.get("assignees", [])
        if isinstance(assignees, list) and assignee_name in assignees:
            return True

        # Check tags (some DBs use tags for assignees)
        if assignee_name in task.tags:
            return True

        return False

    return _filter


def tag_filter(tag: str) -> Callable[[Task], bool]:
    """Create a filter that matches tasks with a specific tag."""
    def _filter(task: Task) -> bool:
        return tag in task.tags

    return _filter


def priority_filter(
    priorities: list[TaskPriority],
) -> Callable[[Task], bool]:
    """Create a filter that matches tasks with specific priorities."""
    def _filter(task: Task) -> bool:
        return task.priority in priorities

    return _filter


def status_filter(statuses: list[TaskStatus]) -> Callable[[Task], bool]:
    """Create a filter that matches tasks with specific statuses."""
    def _filter(task: Task) -> bool:
        return task.status in statuses

    return _filter


def combine_filters(
    *filters: Callable[[Task], bool], mode: str = "and"
) -> Callable[[Task], bool]:
    """Combine multiple filters.

    Args:
        *filters: Filter functions to combine
        mode: "and" (all must match) or "or" (any must match)
    """
    def _combined(task: Task) -> bool:
        if mode == "and":
            return all(f(task) for f in filters)
        else:
            return any(f(task) for f in filters)

    return _combined


# Predefined field mappers for common transformations


def strip_tags_mapper(tags_to_remove: list[str]) -> Callable[[Task], Task]:
    """Create a mapper that removes specific tags."""
    def _mapper(task: Task) -> Task:
        new_tags = [t for t in task.tags if t not in tags_to_remove]
        return replace(task, tags=new_tags)

    return _mapper


def add_tags_mapper(tags_to_add: list[str]) -> Callable[[Task], Task]:
    """Create a mapper that adds specific tags."""
    def _mapper(task: Task) -> Task:
        new_tags = list(set(task.tags + tags_to_add))
        return replace(task, tags=new_tags)

    return _mapper


def prefix_title_mapper(prefix: str) -> Callable[[Task], Task]:
    """Create a mapper that adds a prefix to the title."""
    def _mapper(task: Task) -> Task:
        if not task.title.startswith(prefix):
            return replace(task, title=f"{prefix}{task.title}")
        return task

    return _mapper
