"""API route registrations for the FastAPI application."""

from fastapi import APIRouter

from .health import router as health_router
from .chat import router as chat_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(chat_router, tags=["chat"])

__all__ = ["api_router"]
