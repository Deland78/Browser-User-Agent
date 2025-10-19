"""FastAPI application factory for the browser automation agent."""

from fastapi import FastAPI

from .config import configure_logging, settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    configure_logging()

    application = FastAPI(
        title="Browser Automation Agent",
        version="0.1.0",
        description=(
            "Backend service for coordinating browser automation, "
            "LLM-driven reasoning, and chat interactions."
        ),
        docs_url="/docs",
    )

    @application.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Simple health endpoint to verify the service is running."""
        return {"status": "ok", "environment": settings.environment}

    return application

