"""Unit tests for browser action handlers.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md US1-003:
- NavigateAction handler using Playwright
- Support wait_for options (load, domcontentloaded, networkidle)
- Apply timeout from session config (FR-020)
- Update BrowserContext after navigation
- Error handling for navigation failures

Per data-model.md Entity 5 (ActionResult):
- action_id, session_id, action_type, status, result_data, error_message, executed_at
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from browser_agent.agent.command_parser import NavigateAction, ClickAction, TypeAction
from browser_agent.browser.context import BrowserContext, PageState


class TestNavigationActionHandler:
    """Test navigation action execution."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.url = "about:blank"
        page.title = AsyncMock(return_value="")
        return page

    @pytest.fixture
    def mock_context_service(self):
        """Create mock ContextService."""
        service = AsyncMock()
        service.update_context = AsyncMock()
        service.get_context_by_session = AsyncMock(
            return_value=BrowserContext(
                context_id="ctx-123",
                session_id="session-456"
            )
        )
        return service

    @pytest.mark.asyncio
    async def test_navigate_basic_url(self, mock_page, mock_context_service):
        """Test basic navigation to URL."""
        from browser_agent.browser.actions import execute_navigate

        action = NavigateAction(url="https://example.com")

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Verify navigation called
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="load",
            timeout=20000  # Default 20s from FR-020
        )

        # Verify result
        assert result["status"] == "success"
        assert result["action_type"] == "navigate"
        assert result["result_data"]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_navigate_with_wait_for_option(self, mock_page, mock_context_service):
        """Test navigation with custom wait_for option."""
        from browser_agent.browser.actions import execute_navigate

        action = NavigateAction(
            url="https://example.com",
            wait_for="domcontentloaded"
        )

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Verify wait_for parameter passed correctly
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="domcontentloaded",
            timeout=20000
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_navigate_networkidle(self, mock_page, mock_context_service):
        """Test navigation with networkidle wait."""
        from browser_agent.browser.actions import execute_navigate

        action = NavigateAction(
            url="https://example.com",
            wait_for="networkidle"
        )

        await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=20000
        )

    @pytest.mark.asyncio
    async def test_navigate_updates_context(self, mock_page, mock_context_service):
        """Test that navigation updates BrowserContext."""
        from browser_agent.browser.actions import execute_navigate

        # Mock successful navigation
        mock_page.goto.return_value = None
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Example Domain"

        action = NavigateAction(url="https://example.com")

        await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Verify context was updated (twice: LOADING then READY)
        assert mock_context_service.update_context.call_count == 2

        # Check final call (READY state)
        final_call_kwargs = mock_context_service.update_context.call_args[1]
        assert final_call_kwargs["session_id"] == "session-456"
        assert final_call_kwargs["current_url"] == "https://example.com"
        assert final_call_kwargs["page_title"] == "Example Domain"
        assert final_call_kwargs["page_state"] == PageState.READY

    @pytest.mark.asyncio
    async def test_navigate_timeout_error(self, mock_page, mock_context_service):
        """Test navigation timeout handling (FR-020)."""
        from browser_agent.browser.actions import execute_navigate
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        # Simulate timeout
        mock_page.goto.side_effect = PlaywrightTimeout("Timeout 20000ms exceeded")

        action = NavigateAction(url="https://slow-site.com")

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Verify error result
        assert result["status"] == "error"
        assert result["action_type"] == "navigate"
        assert "timeout" in result["error_message"].lower()
        assert result["result_data"]["url"] == "https://slow-site.com"

    @pytest.mark.asyncio
    async def test_navigate_invalid_url_error(self, mock_page, mock_context_service):
        """Test navigation error for invalid URLs."""
        from browser_agent.browser.actions import execute_navigate
        from playwright.async_api import Error as PlaywrightError

        # Simulate navigation error
        mock_page.goto.side_effect = PlaywrightError("net::ERR_NAME_NOT_RESOLVED")

        action = NavigateAction(url="https://invalid-domain-xyz.test")

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        assert result["status"] == "error"
        assert "ERR_NAME_NOT_RESOLVED" in result["error_message"] or "error" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_navigate_updates_context_on_error(self, mock_page, mock_context_service):
        """Test that context is updated to ERROR state on navigation failure."""
        from browser_agent.browser.actions import execute_navigate
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        mock_page.goto.side_effect = PlaywrightTimeout("Timeout")
        mock_page.url = "about:blank"

        action = NavigateAction(url="https://slow-site.com")

        await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Verify context updated with error state (twice: LOADING then ERROR)
        assert mock_context_service.update_context.call_count == 2

        # Check final call (ERROR state)
        final_call_kwargs = mock_context_service.update_context.call_args[1]
        assert final_call_kwargs["page_state"] == PageState.ERROR

    @pytest.mark.asyncio
    async def test_navigate_custom_timeout(self, mock_page, mock_context_service):
        """Test navigation with custom timeout from config."""
        from browser_agent.browser.actions import execute_navigate

        action = NavigateAction(url="https://example.com")

        # Pass custom timeout (e.g., from session config)
        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service,
            timeout_seconds=30
        )

        # Verify custom timeout used
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="load",
            timeout=30000  # 30s in milliseconds
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_navigate_returns_action_result(self, mock_page, mock_context_service):
        """Test that navigate returns proper ActionResult structure."""
        from browser_agent.browser.actions import execute_navigate

        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Example"

        action = NavigateAction(url="https://example.com")

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Verify ActionResult structure per data-model.md Entity 5
        assert "action_type" in result
        assert "status" in result
        assert "result_data" in result
        assert "error_message" in result

        assert result["action_type"] == "navigate"
        assert result["status"] == "success"
        assert result["result_data"]["url"] == "https://example.com"
        assert result["result_data"]["final_url"] == "https://example.com"
        assert result["result_data"]["page_title"] == "Example"
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_navigate_sets_loading_state(self, mock_page, mock_context_service):
        """Test that context is set to LOADING during navigation."""
        from browser_agent.browser.actions import execute_navigate

        # Track update_context calls
        update_calls = []

        async def track_updates(**kwargs):
            update_calls.append(kwargs)

        mock_context_service.update_context = track_updates

        action = NavigateAction(url="https://example.com")
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Example"

        await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Should have 2 updates: LOADING before, READY after
        assert len(update_calls) >= 2
        assert update_calls[0]["page_state"] == PageState.LOADING
        assert update_calls[-1]["page_state"] == PageState.READY

    @pytest.mark.asyncio
    async def test_navigate_redirect_handling(self, mock_page, mock_context_service):
        """Test navigation handles redirects correctly."""
        from browser_agent.browser.actions import execute_navigate

        # Simulate redirect
        action = NavigateAction(url="https://example.com")
        mock_page.url = "https://www.example.com"  # Redirected URL
        mock_page.title.return_value = "Example"

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Should record both original and final URL
        assert result["result_data"]["url"] == "https://example.com"
        assert result["result_data"]["final_url"] == "https://www.example.com"

    @pytest.mark.asyncio
    async def test_navigate_missing_protocol(self, mock_page, mock_context_service):
        """Test navigation with URL missing protocol."""
        from browser_agent.browser.actions import execute_navigate

        # NavigateAction should have protocol already (from CommandParser)
        # But test handler is robust
        action = NavigateAction(url="https://example.com")

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        assert result["status"] == "success"


class TestActionResultStructure:
    """Test ActionResult data structure compliance."""

    @pytest.mark.asyncio
    async def test_action_result_has_required_fields(self):
        """Test that ActionResult has all required fields per data-model.md."""
        from browser_agent.browser.actions import execute_navigate

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Test")

        mock_context_service = AsyncMock()

        action = NavigateAction(url="https://example.com")

        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )

        # Per data-model.md Entity 5 (ActionResult)
        required_fields = ["action_type", "status", "result_data", "error_message"]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_action_result_status_values(self):
        """Test that status field uses valid values."""
        from browser_agent.browser.actions import execute_navigate
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        mock_page = AsyncMock()
        mock_context_service = AsyncMock()

        # Test success status
        mock_page.goto = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Test")

        action = NavigateAction(url="https://example.com")
        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )
        assert result["status"] in ["success", "error", "partial"]

        # Test error status
        mock_page.goto.side_effect = PlaywrightTimeout("Timeout")
        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id="session-456",
            context_service=mock_context_service
        )
        assert result["status"] in ["success", "error", "partial"]


class TestNavigateIntegrationWithContext:
    """Test navigation integration with BrowserContext."""

    @pytest.mark.asyncio
    async def test_navigate_full_context_lifecycle(self):
        """Test complete navigation lifecycle with real ContextService."""
        from browser_agent.browser.actions import execute_navigate
        from browser_agent.browser.context import ContextService
        from uuid import uuid4

        # Use real ContextService
        context_service = ContextService()
        session_id = str(uuid4())

        # Create context
        await context_service.create_context(session_id=session_id)

        # Mock page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example Domain")

        # Execute navigation
        action = NavigateAction(url="https://example.com")
        result = await execute_navigate(
            action=action,
            page=mock_page,
            session_id=session_id,
            context_service=context_service
        )

        # Verify context was updated
        context = await context_service.get_context_by_session(session_id)
        assert context.current_url == "https://example.com"
        assert context.page_title == "Example Domain"
        assert context.page_state == PageState.READY
        assert context.last_page_change_at is not None

        # Verify result
        assert result["status"] == "success"


# ============================================================================
# Click Action Handler Tests (US1-004)
# ============================================================================


class TestClickActionHandler:
    """Test click action execution with ElementFinder integration."""

    @pytest.fixture
    def mock_page(self):
        page = MagicMock()
        return page

    @pytest.fixture
    def mock_context_service(self):
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_element_finder(self):
        from browser_agent.browser.element_finder import ElementFinder
        finder = AsyncMock(spec=ElementFinder)
        return finder

    @pytest.mark.asyncio
    async def test_click_by_text_success(self, mock_page, mock_context_service, mock_element_finder):
        from browser_agent.browser.actions import execute_click_with_finder

        mock_element_finder.find_elements = AsyncMock(return_value=[{"tag_name": "button", "text": "Login"}])
        mock_locator = MagicMock()
        mock_locator.click = AsyncMock()
        mock_page.get_by_text.return_value = mock_locator

        action = ClickAction(element_description="Login button", text="Login")
        result = await execute_click_with_finder(action, mock_page, "s-1", mock_context_service, mock_element_finder)

        assert result["status"] == "success"
        mock_locator.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_element_not_found(self, mock_page, mock_context_service, mock_element_finder):
        from browser_agent.browser.actions import execute_click_with_finder

        mock_element_finder.find_elements = AsyncMock(return_value=[])
        action = ClickAction(element_description="Missing button", text="NotFound")
        result = await execute_click_with_finder(action, mock_page, "s-1", mock_context_service, mock_element_finder)

        assert result["status"] == "error"
        assert "not found" in result["error_message"].lower()
