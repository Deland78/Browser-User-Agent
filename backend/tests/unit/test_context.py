"""Unit tests for BrowserContext state management.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md INFRA-007:
- BrowserContext state management
- Track current_url, page_title, page_state per data-model.md Entity 4
- Implement get_page_state() method per browser-api.yaml
- Link context to session (one-to-one relationship)

Per data-model.md Entity 4 (BrowserContext):
- context_id, session_id, current_url, page_title, page_state, last_page_change_at
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from browser_agent.browser.context import (
    BrowserContext,
    PageState,
    ContextService,
    ContextNotFoundError,
    ContextAlreadyExistsError,
)


class TestBrowserContext:
    """Test BrowserContext model validation."""

    def test_create_context_with_defaults(self):
        """Test creating a context with default values."""
        context = BrowserContext(
            context_id="ctx-123",
            session_id="session-456"
        )

        assert context.context_id == "ctx-123"
        assert context.session_id == "session-456"
        assert context.page_state == PageState.IDLE
        assert context.current_url is None
        assert context.page_title is None
        assert context.last_page_change_at is None

    def test_create_context_with_page_data(self):
        """Test creating context with page information."""
        now = datetime.now(timezone.utc)
        context = BrowserContext(
            context_id="ctx-123",
            session_id="session-456",
            current_url="https://example.com",
            page_title="Example Domain",
            page_state=PageState.READY,
            last_page_change_at=now
        )

        assert context.current_url == "https://example.com"
        assert context.page_title == "Example Domain"
        assert context.page_state == PageState.READY
        assert context.last_page_change_at == now

    def test_page_state_transitions(self):
        """Test valid page state transitions."""
        context = BrowserContext(
            context_id="ctx-123",
            session_id="session-456"
        )

        # Initial state
        assert context.page_state == PageState.IDLE

        # Transition: idle -> loading
        context.page_state = PageState.LOADING
        assert context.page_state == PageState.LOADING

        # Transition: loading -> ready
        context.page_state = PageState.READY
        assert context.page_state == PageState.READY

        # Transition: ready -> error
        context.page_state = PageState.ERROR
        assert context.page_state == PageState.ERROR

    def test_url_validation(self):
        """Test URL format validation."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://localhost:8000",
            "https://example.com/path?query=1",
            None  # Empty URL is valid for new contexts
        ]

        for url in valid_urls:
            context = BrowserContext(
                context_id=f"ctx-{valid_urls.index(url)}",
                session_id="session-1",
                current_url=url
            )
            assert context.current_url == url


@pytest.mark.asyncio
class TestContextService:
    """Test ContextService CRUD operations with async SQLite."""

    @pytest.fixture
    def service(self):
        """Create a fresh ContextService instance."""
        return ContextService()

    @pytest.fixture
    def session_id(self):
        """Provide a test session ID."""
        return str(uuid4())

    async def test_create_context(self, service, session_id):
        """Test creating a new browser context."""
        context = await service.create_context(session_id=session_id)

        assert context.context_id is not None
        assert len(context.context_id) == 36  # UUID format
        assert context.session_id == session_id
        assert context.page_state == PageState.IDLE
        assert context.current_url is None
        assert context.page_title is None

    async def test_get_context_by_session(self, service, session_id):
        """Test retrieving context by session ID."""
        # Create context
        created_context = await service.create_context(session_id=session_id)

        # Retrieve it
        retrieved_context = await service.get_context_by_session(session_id)

        assert retrieved_context.context_id == created_context.context_id
        assert retrieved_context.session_id == session_id

    async def test_get_context_not_found(self, service):
        """Test retrieving non-existent context raises error."""
        with pytest.raises(ContextNotFoundError) as exc_info:
            await service.get_context_by_session("non-existent-session")

        assert "Context not found" in str(exc_info.value)

    async def test_one_context_per_session(self, service, session_id):
        """Test that only one context can exist per session."""
        # Create first context
        await service.create_context(session_id=session_id)

        # Attempting to create another should fail
        with pytest.raises(ContextAlreadyExistsError) as exc_info:
            await service.create_context(session_id=session_id)

        assert "already exists" in str(exc_info.value)

    async def test_update_page_navigation(self, service, session_id):
        """Test updating context after page navigation."""
        # Create context
        context = await service.create_context(session_id=session_id)

        # Update with navigation data
        updated = await service.update_context(
            session_id=session_id,
            current_url="https://google.com",
            page_title="Google",
            page_state=PageState.READY
        )

        assert updated.current_url == "https://google.com"
        assert updated.page_title == "Google"
        assert updated.page_state == PageState.READY
        assert updated.last_page_change_at is not None

    async def test_update_page_state_only(self, service, session_id):
        """Test updating only page state (e.g., loading indicator)."""
        # Create context with initial page
        context = await service.create_context(session_id=session_id)
        await service.update_context(
            session_id=session_id,
            current_url="https://example.com",
            page_state=PageState.READY
        )

        # Update just the state (simulating navigation start)
        updated = await service.update_context(
            session_id=session_id,
            page_state=PageState.LOADING
        )

        assert updated.page_state == PageState.LOADING
        assert updated.current_url == "https://example.com"  # Unchanged

    async def test_get_page_state(self, service, session_id):
        """Test get_page_state() method returns current state."""
        # Create and navigate
        await service.create_context(session_id=session_id)
        await service.update_context(
            session_id=session_id,
            current_url="https://example.com",
            page_title="Example",
            page_state=PageState.READY
        )

        # Get state summary
        state = await service.get_page_state(session_id)

        assert state["current_url"] == "https://example.com"
        assert state["page_title"] == "Example"
        assert state["page_state"] == PageState.READY.value
        assert "last_page_change_at" in state

    async def test_delete_context(self, service, session_id):
        """Test deleting a context."""
        # Create context
        await service.create_context(session_id=session_id)

        # Delete it
        await service.delete_context(session_id)

        # Should not be retrievable
        with pytest.raises(ContextNotFoundError):
            await service.get_context_by_session(session_id)

    async def test_session_isolation(self, service):
        """Test contexts are isolated by session."""
        session1 = str(uuid4())
        session2 = str(uuid4())

        # Create contexts for different sessions
        ctx1 = await service.create_context(session_id=session1)
        ctx2 = await service.create_context(session_id=session2)

        # Navigate each to different pages
        await service.update_context(
            session_id=session1,
            current_url="https://google.com"
        )
        await service.update_context(
            session_id=session2,
            current_url="https://example.com"
        )

        # Verify isolation
        state1 = await service.get_page_state(session1)
        state2 = await service.get_page_state(session2)

        assert state1["current_url"] == "https://google.com"
        assert state2["current_url"] == "https://example.com"

    async def test_error_state_tracking(self, service, session_id):
        """Test tracking page load errors."""
        # Create context
        await service.create_context(session_id=session_id)

        # Simulate navigation error
        updated = await service.update_context(
            session_id=session_id,
            current_url="https://invalid-url.test",
            page_state=PageState.ERROR
        )

        assert updated.page_state == PageState.ERROR
        assert updated.current_url == "https://invalid-url.test"

    async def test_last_page_change_timestamp(self, service, session_id):
        """Test that last_page_change_at updates on navigation."""
        # Create context
        await service.create_context(session_id=session_id)

        # First navigation
        ctx1 = await service.update_context(
            session_id=session_id,
            current_url="https://page1.com",
            page_state=PageState.READY
        )
        first_change = ctx1.last_page_change_at

        assert first_change is not None

        # Second navigation (should have later timestamp)
        ctx2 = await service.update_context(
            session_id=session_id,
            current_url="https://page2.com",
            page_state=PageState.READY
        )
        second_change = ctx2.last_page_change_at

        assert second_change > first_change
