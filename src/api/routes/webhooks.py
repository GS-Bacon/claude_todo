"""Webhook routes for Slack and Discord."""

from typing import Any
from fastapi import APIRouter, Request, Response, HTTPException

from ...services.mention_service import MentionService
from ...container import get_container

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_mention_service() -> MentionService:
    """Get MentionService from container."""
    container = get_container()
    return container.mention_service


@router.post("/slack")
async def slack_webhook(request: Request) -> dict[str, Any]:
    """Handle Slack webhook events.

    Supports:
    - URL verification challenge
    - Event callbacks (app_mention, message)
    """
    payload = await request.json()

    # Handle URL verification
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # Handle event callbacks
    if payload.get("type") == "event_callback":
        service = get_mention_service()
        task = await service.process_webhook(payload)

        if task:
            return {
                "status": "success",
                "message": "Task created",
                "task_id": task.id.value,
            }

    return {"status": "ok"}


@router.post("/discord")
async def discord_webhook(request: Request) -> dict[str, Any]:
    """Handle Discord webhook events.

    Supports:
    - Ping (type 1)
    - Message events
    """
    payload = await request.json()

    # Handle Discord ping (verification)
    if payload.get("type") == 1:
        return {"type": 1}

    # Handle message events
    service = get_mention_service()
    task = await service.process_webhook(payload)

    if task:
        return {
            "status": "success",
            "message": "Task created",
            "task_id": task.id.value,
        }

    return {"status": "ok"}


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for webhooks."""
    return {"status": "healthy"}
