"""Integration tests for browser driver with real Playwright browser."""

import pytest
import pytest_asyncio

from browser_agent.browser.driver import PlaywrightBrowserService, BrowserError


@pytest.mark.integration
class TestPlaywrightBrowserIntegration:
    """Integration tests with real browser instance."""

    @pytest_asyncio.fixture
    async def browser_service(self):
        """Create and initialize a real browser service."""
        service = PlaywrightBrowserService()
        await service.initialize()
        yield service
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_real_browser_launch(self, browser_service):
        """Test launching a real browser instance."""
        assert browser_service.is_initialized

    @pytest.mark.asyncio
    async def test_create_and_close_real_context(self, browser_service):
        """Test creating and closing a real browser context."""
        session_id = "integration-test-session"

        # Create context
        context_id = await browser_service.create_context(
            session_id=session_id,
            viewport_width=1024,
            viewport_height=768,
        )

        assert context_id is not None

        # Get page
        page = await browser_service.get_page(context_id)
        assert page is not None

        # Close context
        await browser_service.close_context(context_id)

        # Verify context is closed
        assert browser_service.get_context_for_session(session_id) is None

    @pytest.mark.asyncio
    async def test_navigate_to_url(self, browser_service):
        """Test navigating to a real URL."""
        session_id = "integration-nav-test"

        # Create context
        context_id = await browser_service.create_context(session_id=session_id)

        # Get page
        page = await browser_service.get_page(context_id)

        # Navigate to a real page
        await page.goto("https://example.com")

        # Verify navigation
        assert "example.com" in page.url.lower()

        # Cleanup
        await browser_service.close_context(context_id)

    @pytest.mark.asyncio
    async def test_multiple_contexts(self, browser_service):
        """Test creating multiple independent browser contexts."""
        session_1 = "session-1"
        session_2 = "session-2"

        # Create two contexts
        context_1 = await browser_service.create_context(session_1)
        context_2 = await browser_service.create_context(session_2)

        # Verify they are different
        assert context_1 != context_2

        # Get pages for both
        page_1 = await browser_service.get_page(context_1)
        page_2 = await browser_service.get_page(context_2)

        # Navigate to different URLs
        await page_1.goto("https://example.com")
        await page_2.goto("https://example.org")

        # Verify independence
        assert "example.com" in page_1.url.lower()
        assert "example.org" in page_2.url.lower()

        # Cleanup
        await browser_service.close_context(context_1)
        await browser_service.close_context(context_2)
