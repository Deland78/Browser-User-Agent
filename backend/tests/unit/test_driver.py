"""Unit tests for browser driver with mocked Playwright."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from browser_agent.browser.driver import (
    PlaywrightBrowserService,
    BrowserError,
    ContextNotFoundError,
)


class TestPlaywrightBrowserService:
    """Test suite for PlaywrightBrowserService."""

    @pytest.fixture
    def mock_playwright(self):
        """Create mocked Playwright objects."""
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Setup mock chain
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.pages = [mock_page]

        return {
            "playwright": mock_pw,
            "browser": mock_browser,
            "context": mock_context,
            "page": mock_page,
        }

    @pytest_asyncio.fixture
    async def service(self, mock_playwright):
        """Create browser service with mocked Playwright."""
        service = PlaywrightBrowserService()

        with patch("browser_agent.browser.driver.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(
                return_value=mock_playwright["playwright"]
            )
            await service.initialize()

        yield service

        # Cleanup
        if service.is_initialized:
            await service.shutdown()

    @pytest.mark.asyncio
    async def test_initialization(self, mock_playwright):
        """Test browser service initialization."""
        service = PlaywrightBrowserService()
        assert not service.is_initialized

        with patch("browser_agent.browser.driver.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(
                return_value=mock_playwright["playwright"]
            )
            await service.initialize()

        assert service.is_initialized
        mock_playwright["playwright"].chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_idempotent(self, service):
        """Test that calling initialize multiple times is safe."""
        # Already initialized in fixture
        assert service.is_initialized

        # Call again
        await service.initialize()

        # Should still be initialized
        assert service.is_initialized

    @pytest.mark.asyncio
    async def test_create_context(self, service, mock_playwright):
        """Test creating a browser context."""
        session_id = "test-session-123"

        context_id = await service.create_context(
            session_id=session_id,
            viewport_width=1920,
            viewport_height=1080,
        )

        # Verify context_id is a valid UUID
        assert UUID(context_id)

        # Verify browser.new_context was called with viewport
        mock_playwright["browser"].new_context.assert_called_once()
        call_kwargs = mock_playwright["browser"].new_context.call_args[1]
        assert call_kwargs["viewport"] == {"width": 1920, "height": 1080}

        # Verify new page was created
        mock_playwright["context"].new_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_context_default_viewport(self, service, mock_playwright):
        """Test creating context with default viewport."""
        session_id = "test-session-456"

        context_id = await service.create_context(session_id=session_id)

        # Verify default viewport dimensions
        call_kwargs = mock_playwright["browser"].new_context.call_args[1]
        assert call_kwargs["viewport"] == {"width": 1280, "height": 720}

    @pytest.mark.asyncio
    async def test_create_context_duplicate_session(self, service):
        """Test creating context for same session returns existing context."""
        session_id = "test-session-789"

        # Create first context
        context_id_1 = await service.create_context(session_id=session_id)

        # Attempt to create second context for same session
        context_id_2 = await service.create_context(session_id=session_id)

        # Should return same context ID
        assert context_id_1 == context_id_2

    @pytest.mark.asyncio
    async def test_create_context_not_initialized(self):
        """Test creating context before initialization raises error."""
        service = PlaywrightBrowserService()

        with pytest.raises(BrowserError, match="not initialized"):
            await service.create_context(session_id="test-session")

    @pytest.mark.asyncio
    async def test_get_page(self, service, mock_playwright):
        """Test retrieving page from context."""
        session_id = "test-session"
        context_id = await service.create_context(session_id=session_id)

        page = await service.get_page(context_id)

        assert page == mock_playwright["page"]

    @pytest.mark.asyncio
    async def test_get_page_context_not_found(self, service):
        """Test getting page for non-existent context raises error."""
        with pytest.raises(ContextNotFoundError, match="not found"):
            await service.get_page("non-existent-context-id")

    @pytest.mark.asyncio
    async def test_get_page_creates_new_if_none_exist(self, service, mock_playwright):
        """Test that get_page creates a new page if none exist."""
        session_id = "test-session"
        context_id = await service.create_context(session_id=session_id)

        # Mock context with no pages
        mock_context = mock_playwright["context"]
        mock_context.pages = []

        new_page_mock = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=new_page_mock)

        page = await service.get_page(context_id)

        assert page == new_page_mock
        mock_context.new_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_context(self, service, mock_playwright):
        """Test closing a browser context."""
        session_id = "test-session"
        context_id = await service.create_context(session_id=session_id)

        # Close context
        await service.close_context(context_id)

        # Verify context was closed
        mock_playwright["context"].close.assert_called_once()

        # Verify context is removed from tracking
        with pytest.raises(ContextNotFoundError):
            await service.get_page(context_id)

    @pytest.mark.asyncio
    async def test_close_context_not_found(self, service):
        """Test closing non-existent context raises error."""
        with pytest.raises(ContextNotFoundError, match="not found"):
            await service.close_context("non-existent-context-id")

    @pytest.mark.asyncio
    async def test_get_context_for_session(self, service):
        """Test retrieving context ID for a session."""
        session_id = "test-session"
        context_id = await service.create_context(session_id=session_id)

        retrieved_context_id = service.get_context_for_session(session_id)

        assert retrieved_context_id == context_id

    @pytest.mark.asyncio
    async def test_get_context_for_session_not_found(self, service):
        """Test getting context for non-existent session returns None."""
        context_id = service.get_context_for_session("non-existent-session")

        assert context_id is None

    @pytest.mark.asyncio
    async def test_shutdown(self, service, mock_playwright):
        """Test shutting down browser service."""
        session_id = "test-session"
        await service.create_context(session_id=session_id)

        await service.shutdown()

        # Verify all resources were cleaned up
        assert not service.is_initialized
        mock_playwright["context"].close.assert_called_once()
        mock_playwright["browser"].close.assert_called_once()
        mock_playwright["playwright"].stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self, service, mock_playwright):
        """Test that calling shutdown multiple times is safe."""
        await service.shutdown()

        # Reset mocks
        mock_playwright["browser"].close.reset_mock()
        mock_playwright["playwright"].stop.reset_mock()

        # Call shutdown again
        await service.shutdown()

        # Should not call close/stop again
        mock_playwright["browser"].close.assert_not_called()
        mock_playwright["playwright"].stop.assert_not_called()
