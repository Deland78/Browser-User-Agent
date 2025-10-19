"""Entrypoint for running the FastAPI application with Uvicorn."""

import uvicorn

from .app import create_app


def run() -> None:
    """Run the development server."""
    uvicorn.run(
        "browser_agent.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


app = create_app()

if __name__ == "__main__":
    run()

