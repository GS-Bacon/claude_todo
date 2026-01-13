"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import webhooks_router, tasks_router
from ..container import get_container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    container = get_container()
    # Initialize services here if needed
    yield
    # Shutdown
    # Clean up resources here if needed


def create_app(
    title: str = "Task Manager API",
    version: str = "1.0.0",
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create FastAPI application.

    Args:
        title: API title
        version: API version
        cors_origins: Allowed CORS origins

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title=title,
        version=version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include routers
    app.include_router(webhooks_router)
    app.include_router(tasks_router)

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "version": version}

    return app


# Create default app instance
app = create_app()
