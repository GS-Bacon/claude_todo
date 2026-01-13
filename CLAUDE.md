# CLAUDE.md - Project Guidelines

This file provides guidance to Claude Code (claude.ai/code) when working with this codebase.

## Project Overview

**claude-todo** is a task management system that integrates with Notion, Slack, and Discord. It provides:
- CLI for task management operations
- REST API for webhooks and task CRUD
- Scheduled jobs for syncing and notifications
- Multi-source task aggregation (team + personal)

## Architecture

### Directory Structure

```
src/
├── domain/          # Core domain models and protocols (interfaces)
│   ├── models.py    # Task, Mention, Notification dataclasses
│   └── protocols.py # Repository and service protocols
├── repositories/    # Data persistence implementations
│   ├── notion.py    # Notion API integration
│   └── memory.py    # In-memory implementation (testing/dev)
├── services/        # Business logic layer
│   ├── task_service.py        # Task CRUD with caching
│   ├── mention_service.py     # Webhook processing
│   └── notification_service.py # Notification dispatch
├── api/             # FastAPI REST API
│   ├── app.py       # Application factory
│   └── routes/      # Endpoint definitions
├── cli/             # Click CLI commands
│   └── main.py      # All CLI commands
├── scheduler/       # APScheduler job management
│   ├── jobs.py      # Job definitions and registry
│   └── scheduler.py # Scheduler wrapper
├── notifications/   # Notification senders
│   └── discord_sender.py
├── parsers/         # Webhook payload parsers
│   ├── slack_parser.py
│   └── discord_parser.py
├── config/          # Pydantic settings
│   └── settings.py
└── container.py     # Dependency injection container
```

### Key Design Patterns

1. **Protocol-based DI**: All dependencies use `typing.Protocol` for loose coupling
2. **Repository Pattern**: Data access abstracted through `TaskRepository` protocol
3. **Service Layer**: Business logic isolated in service classes
4. **Lazy Providers**: Container uses lazy initialization for dependencies

### Domain Models

- `Task`: Core entity with status, priority, source, due date, tags
- `TaskId`: Value object for task identification (supports Notion ID format)
- `Mention`: Parsed webhook data from Slack/Discord
- `Notification`: Outgoing notification payload
- `TaskFilter`: Query criteria for listing tasks

## Common Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test file
pytest tests/unit/test_task_service.py

# Run with coverage
pytest --cov=src

# Start API server
claude-todo serve --port 8000

# CLI commands
claude-todo list                    # List all tasks
claude-todo list --status todo      # Filter by status
claude-todo show <task_id>          # Show task details
claude-todo complete <task_id>      # Mark complete
claude-todo due-today               # Show today's tasks
claude-todo overdue                 # Show overdue tasks
claude-todo summary                 # Show task summary
claude-todo sync                    # Sync from Notion
claude-todo jobs                    # List scheduled jobs
claude-todo run-job <job_name>      # Run job manually
```

## Development Guidelines

### Adding a New Repository

1. Implement `TaskRepository` protocol from `src/domain/protocols.py`
2. Register in container via `configure_task_repository()` or `configure_personal_task_repository()`

### Adding a New Notification Sender

1. Implement `NotificationSender` protocol
2. Add to container via `add_notification_sender()`

### Adding a New Webhook Parser

1. Implement `WebhookParser` protocol
2. Add to `MentionService` parsers list in container

### Testing

- Unit tests in `tests/unit/`
- API tests in `tests/api/`
- Use `InMemoryTaskRepository` and `InMemoryCacheRepository` for testing
- Use `reset_container()` in test fixtures

## Environment Variables

```bash
# Notion - Basic
NOTION_API_KEY=secret_xxx
NOTION_TEAM_DATABASE_ID=xxx
NOTION_PERSONAL_DATABASE_ID=xxx
NOTION_API_VERSION=2022-06-28

# Notion - Property Names (customize to match your database)
NOTION_PROP_TITLE=Name
NOTION_PROP_STATUS=Status
NOTION_PROP_PRIORITY=Priority
NOTION_PROP_DUE_DATE=Due
NOTION_PROP_TAGS=Tags
NOTION_PROP_DESCRIPTION=Description
NOTION_PROP_ASSIGNEE=Assignee
NOTION_PROP_METADATA=Metadata
NOTION_PROP_CREATED=Created

# Notion - Status Values (customize to match your database)
NOTION_STATUS_TODO=Not started
NOTION_STATUS_IN_PROGRESS=In progress
NOTION_STATUS_DONE=Done
NOTION_STATUS_BLOCKED=Blocked

# Notion - Priority Values (customize to match your database)
NOTION_PRIORITY_LOW=Low
NOTION_PRIORITY_MEDIUM=Medium
NOTION_PRIORITY_HIGH=High
NOTION_PRIORITY_URGENT=Urgent

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx

# Slack
SLACK_SIGNING_SECRET=xxx
SLACK_BOT_TOKEN=xoxb-xxx

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=Asia/Tokyo
SCHEDULER_SYNC_CRON=*/15 * * * *
SCHEDULER_NOTIFICATION_CRON=0 9 * * *

# App
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

## Notion Database Configuration

### Property Name Mapping

All Notion property names are configurable via environment variables. This allows you to use your existing database without renaming properties.

Settings classes in `src/config/settings.py`:

- `NotionPropertyNames`: Maps internal names to your Notion property names
- `NotionStatusMapping`: Maps TaskStatus enum to your Notion status values
- `NotionPriorityMapping`: Maps TaskPriority enum to your Notion priority values

### Default Schema

If using defaults, create a Notion database with these properties:

| Property | Type | Values |
|----------|------|--------|
| Name | Title | - |
| Status | Status | Not started, In progress, Done, Blocked |
| Priority | Select | Low, Medium, High, Urgent |
| Due | Date | - |
| Tags | Multi-select | - |
| Description | Rich text | - |
| Assignee | People | - |
| Metadata | Rich text | JSON string |
| Created | Created time | - |

### Example: Japanese Property Names

```bash
NOTION_PROP_TITLE=タスク名
NOTION_PROP_STATUS=ステータス
NOTION_PROP_PRIORITY=優先度
NOTION_PROP_DUE_DATE=期限
NOTION_PROP_TAGS=タグ
NOTION_PROP_DESCRIPTION=説明

NOTION_STATUS_TODO=未着手
NOTION_STATUS_IN_PROGRESS=進行中
NOTION_STATUS_DONE=完了
NOTION_STATUS_BLOCKED=ブロック中

NOTION_PRIORITY_LOW=低
NOTION_PRIORITY_MEDIUM=中
NOTION_PRIORITY_HIGH=高
NOTION_PRIORITY_URGENT=緊急
```

## API Endpoints

- `GET /health` - Health check
- `GET /tasks` - List tasks
- `GET /tasks/{task_id}` - Get task
- `POST /tasks` - Create task
- `PATCH /tasks/{task_id}` - Update task
- `DELETE /tasks/{task_id}` - Delete task
- `POST /webhooks/slack` - Slack events
- `POST /webhooks/discord` - Discord events
