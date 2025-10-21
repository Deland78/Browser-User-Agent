"""Unit tests for CommandExecutor.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md US1-007:
- CommandExecutor class with execute() method
- Coordinate action execution via BrowserService
- Handle errors and timeouts per FR-009
- Return ExecutionResult with success status and message

Per agent-interface.md CommandExecutor specification:
- execute() accepts parsed_command, browser_context, progress_callback
- Returns ExecutionResult with success, message, actions_executed, extracted_data, duration_ms, errors
- Raises ExecutionError, TimeoutError, CancelledError
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import List, Optional

from browser_agent.agent.command_parser import (
    ParsedCommand,
    CommandIntent,
    NavigateAction,
    ClickAction,
    TypeAction,
)
from browser_agent.agent.executor import (
    CommandExecutor,
    ExecutionResult,
    ExecutionError,
)
from browser_agent.browser.context import BrowserContext, PageState


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_execution_result_success(self):
        """Test ExecutionResult structure for successful execution."""
        result = ExecutionResult(
            success=True,
            message="Successfully navigated to google.com",
            actions_executed=[NavigateAction(url="https://google.com")],
            extracted_data=None,
            duration_ms=1200,
            errors=[]
        )

        assert result.success is True
        assert "google.com" in result.message
        assert len(result.actions_executed) == 1
        assert result.duration_ms == 1200
        assert result.errors == []

    def test_execution_result_failure(self):
        """Test ExecutionResult structure for failed execution."""
        error = ExecutionError("Page load timeout")

        result = ExecutionResult(
            success=False,
            message="Failed to navigate: Page load timeout",
            actions_executed=[],
            extracted_data=None,
            duration_ms=20000,
            errors=[error]
        )

        assert result.success is False
        assert "timeout" in result.message.lower()
        assert len(result.errors) == 1
        assert result.duration_ms == 20000


class TestCommandExecutor:
    """Test CommandExecutor class."""

    @pytest.fixture
    def mock_browser_service(self):
        """Create mock BrowserService."""
        service = Mock()
        service.get_page = AsyncMock()
        return service

    @pytest.fixture
    def mock_context_service(self):
        """Create mock ContextService."""
        service = Mock()
        service.update_context = AsyncMock()
        return service

    @pytest.fixture
    def browser_context(self):
        """Create sample BrowserContext."""
        return BrowserContext(
            context_id="ctx-123",
            session_id="session-abc",
            page_state=PageState.READY,
            current_url="https://example.com",
            page_title="Example Domain"
        )

    @pytest.fixture
    def executor(self, mock_browser_service, mock_context_service):
        """Create CommandExecutor instance."""
        return CommandExecutor(
            browser_service=mock_browser_service,
            context_service=mock_context_service
        )

    @pytest.mark.asyncio
    async def test_executor_initialization(self, executor, mock_browser_service, mock_context_service):
        """Test CommandExecutor can be initialized with services."""
        assert executor.browser_service == mock_browser_service
        assert executor.context_service == mock_context_service

    @pytest.mark.asyncio
    async def test_execute_single_navigate_action(self, executor, browser_context, mock_browser_service):
        """Test executing single navigation action."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to google.com",
            intent=CommandIntent.NAVIGATE,
            actions=[NavigateAction(url="https://google.com", wait_for="load")],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        # Mock page
        mock_page = AsyncMock()
        mock_page.url = "https://google.com"
        mock_page.title = AsyncMock(return_value="Google")
        mock_browser_service.get_page.return_value = mock_page

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.success is True
        assert "google.com" in result.message
        assert len(result.actions_executed) == 1
        assert result.duration_ms > 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_execute_multi_step_actions(self, executor, browser_context, mock_browser_service):
        """Test executing multi-step command with progress tracking."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to google.com and type 'weather' in search",
            intent=CommandIntent.INTERACT,
            actions=[
                NavigateAction(url="https://google.com"),
                TypeAction(element_description="search box", text="weather", selector="input[name=q]")
            ],
            confidence_score=0.92,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        mock_page.url = "https://google.com"
        mock_page.title = AsyncMock(return_value="Google")
        mock_browser_service.get_page.return_value = mock_page

        progress_updates = []

        def track_progress(update):
            progress_updates.append(update)

        # Act
        result = await executor.execute(
            parsed_command,
            browser_context,
            progress_callback=track_progress
        )

        # Assert
        assert result.success is True
        assert len(result.actions_executed) == 2
        assert len(progress_updates) == 2  # One update per action
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_handles_navigation_error(self, executor, browser_context, mock_browser_service):
        """Test CommandExecutor handles navigation errors gracefully."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to invalid-url",
            intent=CommandIntent.NAVIGATE,
            actions=[NavigateAction(url="https://invalid-url-that-does-not-exist.com")],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed: net::ERR_NAME_NOT_RESOLVED"))
        mock_browser_service.get_page.return_value = mock_page

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.success is False
        assert "failed" in result.message.lower() or "error" in result.message.lower()
        assert len(result.errors) > 0
        assert result.errors[0].message is not None

    @pytest.mark.asyncio
    async def test_execute_handles_timeout(self, executor, browser_context, mock_browser_service):
        """Test CommandExecutor handles timeout errors."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to slow-site.com",
            intent=CommandIntent.NAVIGATE,
            actions=[NavigateAction(url="https://slow-site.com")],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        # Simulate timeout error
        mock_page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout exceeded 20000ms"))
        mock_browser_service.get_page.return_value = mock_page

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.success is False
        assert "timeout" in result.message.lower()
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_with_empty_actions(self, executor, browser_context):
        """Test CommandExecutor handles ParsedCommand with no actions."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="unclear command",
            intent=CommandIntent.INTERACT,
            actions=[],  # No actions
            confidence_score=0.50,
            ambiguities=["Command unclear"],
            context_used=[]
        )

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.success is False
        assert "no actions" in result.message.lower()
        assert result.actions_executed == []

    @pytest.mark.asyncio
    async def test_execute_stops_on_multi_step_failure(self, executor, browser_context, mock_browser_service):
        """Test multi-step execution stops on first failure."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to google.com and click login",
            intent=CommandIntent.INTERACT,
            actions=[
                NavigateAction(url="https://google.com"),
                ClickAction(element_description="login button", text="Login")
            ],
            confidence_score=0.90,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        # First action (navigate) succeeds
        mock_page.url = "https://google.com"
        mock_page.title = AsyncMock(return_value="Google")
        # Second action (click) fails
        mock_page.click = AsyncMock(side_effect=Exception("Element not found: Login"))
        mock_browser_service.get_page.return_value = mock_page

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.success is False
        assert len(result.actions_executed) == 1  # Only first action executed
        assert len(result.errors) > 0
        assert "login" in result.message.lower() or "element" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_returns_human_readable_messages(self, executor, browser_context, mock_browser_service):
        """Test ExecutionResult contains human-readable messages per FR-008."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to example.com",
            intent=CommandIntent.NAVIGATE,
            actions=[NavigateAction(url="https://example.com")],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example Domain")
        mock_browser_service.get_page.return_value = mock_page

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.success is True
        assert isinstance(result.message, str)
        assert len(result.message) > 0
        # Message should be user-friendly, not technical
        assert "example.com" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_tracks_duration(self, executor, browser_context, mock_browser_service):
        """Test execution duration is measured in milliseconds."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to example.com",
            intent=CommandIntent.NAVIGATE,
            actions=[NavigateAction(url="https://example.com")],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example")
        mock_browser_service.get_page.return_value = mock_page

        # Act
        result = await executor.execute(parsed_command, browser_context)

        # Assert
        assert result.duration_ms >= 0
        assert isinstance(result.duration_ms, int)

    @pytest.mark.asyncio
    async def test_execute_respects_session_timeout(self, executor, browser_context, mock_browser_service):
        """Test executor uses session timeout configuration."""
        # Arrange
        parsed_command = ParsedCommand(
            original_input="Go to example.com",
            intent=CommandIntent.NAVIGATE,
            actions=[NavigateAction(url="https://example.com")],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example")
        mock_browser_service.get_page.return_value = mock_page

        # Act - pass timeout_seconds parameter
        result = await executor.execute(
            parsed_command,
            browser_context,
            timeout_seconds=30  # Custom timeout
        )

        # Assert
        assert result.success is True
        # Note: actual timeout verification would be in action handler tests
