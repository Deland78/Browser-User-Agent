"""API route registrations for the FastAPI application."""

from fastapi import APIRouter

from .health import router as health_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health_router, tags=["health"])

__all__ = ["api_router"]
