"""FastAPI application factory for the browser automation agent."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import api_router
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

    # Configure CORS for frontend origin
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes with /api/v1 prefix
    application.include_router(api_router, prefix="/api/v1")

    # Global exception handlers
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors with user-friendly messages."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "message": "The request contains invalid data",
                "details": exc.errors(),
            },
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions gracefully."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )

    return application

