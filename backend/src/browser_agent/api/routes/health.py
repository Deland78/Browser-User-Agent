"""Health check endpoints for service monitoring."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from browser_agent.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Health status of the service")
    environment: str = Field(..., description="Current environment (development/production)")
    version: str = Field(default="0.1.0", description="Application version")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check service health status.

    Returns basic health information including:
    - Service status (ok/degraded/down)
    - Current environment
    - Application version

    This endpoint is used by load balancers and monitoring tools.
    """
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        version="0.1.0"
    )
