"""FastAPI application entry point."""

from fastapi import FastAPI

from .config import get_settings
from .routers import topics


def create_app() -> FastAPI:
    """Application factory used for tests and worker processes."""

    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.include_router(topics.router, prefix="/topics", tags=["topics"])

    @application.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Return service health information."""

        return {"status": "ok", "service": settings.app_name}

    return application


app = create_app()
