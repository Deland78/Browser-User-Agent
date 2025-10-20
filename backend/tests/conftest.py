"""Pytest configuration and shared fixtures.

This module provides test fixtures and configuration for the entire test suite.
"""

import pytest
import pytest_asyncio
from pathlib import Path


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_database():
    """Initialize test database once per test session."""
    from browser_agent.db.init import init_db

    # Initialize database schema
    await init_db()

    yield

    # Cleanup: Remove test database file if it exists
    db_path = Path("backend/browser_agent.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors
