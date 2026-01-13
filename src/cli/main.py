"""CLI commands for task management."""

import asyncio
from typing import Optional

import click

from ..container import get_container, reset_container
from ..repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository


def setup_container():
    """Set up container with default configuration."""
    container = get_container()

    # Check if already configured
    try:
        _ = container.task_repository
        return  # Already configured
    except RuntimeError:
        pass

    # Use in-memory repositories for now
    # In production, you would configure Notion repositories
    container.configure_task_repository(InMemoryTaskRepository)
    container.configure_personal_task_repository(InMemoryTaskRepository)
    container.configure_cache_repository(InMemoryCacheRepository)


def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Task management CLI for Claude Code integration."""
    setup_container()


@cli.command("list")
@click.option("--status", "-s", help="Filter by status (todo, in_progress, done, blocked)")
@click.option("--priority", "-p", help="Filter by priority (low, medium, high, urgent)")
@click.option("--tags", "-t", help="Filter by tags (comma-separated)")
@click.option("--limit", "-l", default=20, help="Maximum number of tasks to show")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_tasks(status: Optional[str], priority: Optional[str], tags: Optional[str], limit: int, output_json: bool):
    """List tasks with optional filters."""
    from ..domain.models import TaskFilter, TaskStatus, TaskPriority

    container = get_container()
    service = container.task_service

    # Build filter
    filter_kwargs = {"limit": limit}

    if status:
        try:
            filter_kwargs["status"] = [TaskStatus(status)]
        except ValueError:
            click.echo(f"Invalid status: {status}", err=True)
            return

    if priority:
        try:
            filter_kwargs["priority"] = [TaskPriority(priority)]
        except ValueError:
            click.echo(f"Invalid priority: {priority}", err=True)
            return

    if tags:
        filter_kwargs["tags"] = [t.strip() for t in tags.split(",")]

    task_filter = TaskFilter(**filter_kwargs)
    tasks = run_async(service.list_tasks(task_filter))

    if output_json:
        import json
        output = {
            "tasks": [
                {
                    "id": t.id.value,
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                }
                for t in tasks
            ],
            "total": len(tasks),
        }
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if not tasks:
            click.echo("No tasks found.")
            return

        click.echo(f"Found {len(tasks)} task(s):\n")
        for task in tasks:
            status_icon = {
                "todo": "📋",
                "in_progress": "🔄",
                "done": "✅",
                "blocked": "🚫",
            }.get(task.status.value, "❓")

            priority_icon = {
                "low": "🟢",
                "medium": "🔵",
                "high": "🟠",
                "urgent": "🔴",
            }.get(task.priority.value, "⚪")

            due_str = ""
            if task.due_date:
                due_str = f" 📅 {task.due_date.strftime('%Y-%m-%d')}"

            click.echo(f"{status_icon} {priority_icon} [{task.id.value[:8]}] {task.title}{due_str}")


@cli.command("show")
@click.argument("task_id")
def show_task(task_id: str):
    """Show task details."""
    from ..domain.models import TaskId

    container = get_container()
    service = container.task_service

    task = run_async(service.get_task(TaskId(task_id)))

    if not task:
        click.echo(f"Task not found: {task_id}", err=True)
        return

    click.echo(f"ID: {task.id.value}")
    click.echo(f"Title: {task.title}")
    click.echo(f"Status: {task.status.value}")
    click.echo(f"Priority: {task.priority.value}")
    click.echo(f"Source: {task.source.value}")

    if task.description:
        click.echo(f"Description: {task.description}")

    if task.due_date:
        click.echo(f"Due Date: {task.due_date.strftime('%Y-%m-%d %H:%M')}")

    if task.tags:
        click.echo(f"Tags: {', '.join(task.tags)}")

    click.echo(f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}")
    click.echo(f"Updated: {task.updated_at.strftime('%Y-%m-%d %H:%M')}")


@cli.command("complete")
@click.argument("task_id")
def complete_task(task_id: str):
    """Mark a task as complete."""
    from ..domain.models import TaskId, TaskStatus

    container = get_container()
    service = container.task_service

    try:
        task = run_async(service.update_task_status(TaskId(task_id), TaskStatus.DONE))
        click.echo(f"✅ Task completed: {task.title}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command("sync")
def sync_tasks():
    """Sync tasks from Notion."""
    container = get_container()
    service = container.task_service

    result = run_async(service.sync_all())

    click.echo(f"✅ Synced {result['team_tasks']} team tasks")
    click.echo(f"✅ Synced {result['personal_tasks']} personal tasks")


@cli.command("due-today")
def due_today():
    """Show tasks due today."""
    container = get_container()
    service = container.task_service

    tasks = run_async(service.get_tasks_due_today())

    if not tasks:
        click.echo("No tasks due today! 🎉")
        return

    click.echo(f"Tasks due today ({len(tasks)}):\n")
    for task in tasks:
        priority_icon = {
            "low": "🟢",
            "medium": "🔵",
            "high": "🟠",
            "urgent": "🔴",
        }.get(task.priority.value, "⚪")

        click.echo(f"{priority_icon} [{task.id.value[:8]}] {task.title}")


@cli.command("overdue")
def overdue():
    """Show overdue tasks."""
    container = get_container()
    service = container.task_service

    tasks = run_async(service.get_overdue_tasks())

    if not tasks:
        click.echo("No overdue tasks! 🎉")
        return

    click.echo(f"⚠️ Overdue tasks ({len(tasks)}):\n")
    for task in tasks:
        days_overdue = 0
        if task.due_date:
            from datetime import datetime
            days_overdue = (datetime.now() - task.due_date).days

        click.echo(f"🔴 [{task.id.value[:8]}] {task.title} ({days_overdue} days overdue)")


@cli.command("run-job")
@click.argument("job_name")
def run_job(job_name: str):
    """Run a scheduled job immediately."""
    from ..scheduler.jobs import JobRegistry, create_default_jobs

    container = get_container()
    registry = JobRegistry()
    create_default_jobs(registry, container)

    job = registry.get(job_name)
    if not job:
        click.echo(f"Job not found: {job_name}", err=True)
        click.echo("Available jobs:")
        for j in registry.list_jobs():
            click.echo(f"  - {j.name}: {j.description}")
        return

    click.echo(f"Running job: {job_name}...")
    result = run_async(registry.run_job(job_name))
    click.echo(f"✅ Job completed: {result}")


@cli.command("jobs")
def list_jobs():
    """List all scheduled jobs."""
    from ..scheduler.jobs import JobRegistry, create_default_jobs

    container = get_container()
    registry = JobRegistry()
    create_default_jobs(registry, container)

    jobs = registry.list_jobs()

    if not jobs:
        click.echo("No jobs configured.")
        return

    click.echo("Scheduled jobs:\n")
    for job in jobs:
        status = "✅" if job.enabled else "⏸️"
        click.echo(f"{status} {job.name}")
        click.echo(f"   Cron: {job.cron}")
        click.echo(f"   Description: {job.description}")
        click.echo()


@cli.command("serve")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the API server."""
    import uvicorn

    click.echo(f"Starting server at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")

    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command("summary")
def summary():
    """Show task summary."""
    from ..domain.models import TaskStatus, TaskPriority

    container = get_container()
    service = container.task_service

    tasks = run_async(service.list_tasks())

    if not tasks:
        click.echo("No tasks found.")
        return

    # Count by status
    status_counts = {}
    for status in TaskStatus:
        count = sum(1 for t in tasks if t.status == status)
        if count > 0:
            status_counts[status.value] = count

    # Count by priority
    priority_counts = {}
    for priority in TaskPriority:
        count = sum(1 for t in tasks if t.priority == priority)
        if count > 0:
            priority_counts[priority.value] = count

    # Due today and overdue
    due_today = sum(1 for t in tasks if t.is_due_today() and t.status != TaskStatus.DONE)
    overdue_count = sum(1 for t in tasks if t.is_overdue())

    click.echo("📊 Task Summary\n")
    click.echo(f"Total tasks: {len(tasks)}\n")

    click.echo("By Status:")
    status_icons = {"todo": "📋", "in_progress": "🔄", "done": "✅", "blocked": "🚫"}
    for status, count in status_counts.items():
        icon = status_icons.get(status, "❓")
        click.echo(f"  {icon} {status}: {count}")

    click.echo("\nBy Priority:")
    priority_icons = {"low": "🟢", "medium": "🔵", "high": "🟠", "urgent": "🔴"}
    for priority, count in priority_counts.items():
        icon = priority_icons.get(priority, "⚪")
        click.echo(f"  {icon} {priority}: {count}")

    if due_today > 0:
        click.echo(f"\n⏰ Due today: {due_today}")
    if overdue_count > 0:
        click.echo(f"⚠️ Overdue: {overdue_count}")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
