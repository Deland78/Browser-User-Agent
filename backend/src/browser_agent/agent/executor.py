"""CommandExecutor for orchestrating browser action execution.

Implements:
- CommandExecutor class for action execution coordination
- ExecutionResult dataclass for execution outcomes
- Error handling per FR-009
- Multi-step command execution per FR-011
- Progress tracking per FR-012

Per tasks.md US1-007:
- Create CommandExecutor with execute() method per agent-interface.md
- Coordinate action execution via BrowserService
- Handle errors and timeouts
- Return ExecutionResult with success status and message

Per agent-interface.md CommandExecutor specification:
- execute() accepts parsed_command, browser_context, progress_callback
- Returns ExecutionResult with success, message, actions_executed, extracted_data, duration_ms, errors
- Raises ExecutionError, TimeoutError, CancelledError
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Callable
from datetime import datetime, timezone

from browser_agent.agent.command_parser import (
    ParsedCommand,
    BrowserAction,
    NavigateAction,
    ClickAction,
    TypeAction,
    ExtractAction,
    ScrollAction,
    ConfigureAction,
)
from browser_agent.browser.context import BrowserContext, ContextService
from browser_agent.browser.driver import BrowserService

logger = logging.getLogger(__name__)


# ============================================================================
# Execution Result Structure
# Per agent-interface.md ExecutionResult specification
# ============================================================================


class ExecutionError(Exception):
    """Raised when browser action execution fails.

    Per agent-interface.md Error Handling Contract:
    - Must provide user-friendly error messages (FR-009)
    - May include retry suggestions (FR-009a)
    - Contains reference to failed action
    """

    def __init__(
        self,
        message: str,
        retry_suggestion: Optional[str] = None,
        failed_action: Optional[BrowserAction] = None
    ):
        """Initialize ExecutionError.

        Args:
            message: Human-readable error description
            retry_suggestion: Actionable suggestion for user (FR-009a)
            failed_action: The action that failed
        """
        super().__init__(message)
        self.message = message
        self.retry_suggestion = retry_suggestion
        self.failed_action = failed_action


@dataclass
class ExecutionResult:
    """Result of command execution.

    Per agent-interface.md ExecutionResult specification.

    Attributes:
        success: Whether execution completed successfully
        message: Human-readable result message (FR-008, FR-009)
        actions_executed: List of actions that were performed
        extracted_data: Data extracted from page (for extraction commands)
        duration_ms: Total execution time in milliseconds
        errors: List of errors encountered (for partial failures)
    """

    success: bool
    message: str
    actions_executed: List[BrowserAction] = field(default_factory=list)
    extracted_data: Optional[Any] = None
    duration_ms: int = 0
    errors: List[ExecutionError] = field(default_factory=list)


@dataclass
class ProgressUpdate:
    """Progress update for multi-step execution (FR-012).

    Attributes:
        step_number: Current step number (1-indexed)
        total_steps: Total number of steps
        message: Human-readable progress message
        action: The action being executed
    """

    step_number: int
    total_steps: int
    message: str
    action: BrowserAction


# ============================================================================
# Command Executor
# Per agent-interface.md CommandExecutor specification
# ============================================================================


class CommandExecutor:
    """Orchestrates browser action execution.

    Per tasks.md US1-007 and agent-interface.md:
    - Execute parsed commands via BrowserService
    - Handle errors and timeouts per FR-009
    - Support multi-step commands per FR-011
    - Emit progress updates per FR-012
    - Return structured ExecutionResult

    Integration Points:
    - Uses BrowserService for browser automation
    - Uses ContextService for state updates
    - Calls action handlers from browser.actions module
    """

    def __init__(
        self,
        browser_service: BrowserService,
        context_service: ContextService
    ):
        """Initialize CommandExecutor.

        Args:
            browser_service: Service for browser automation
            context_service: Service for browser context state management
        """
        self.browser_service = browser_service
        self.context_service = context_service

    async def execute(
        self,
        parsed_command: ParsedCommand,
        browser_context: BrowserContext,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        timeout_seconds: int = 20  # Default from FR-020
    ) -> ExecutionResult:
        """Execute parsed command via browser automation.

        Per agent-interface.md CommandExecutor.execute() specification.

        Args:
            parsed_command: Validated command (confidence >= 0.9)
            browser_context: Active browser context
            progress_callback: Optional callback for multi-step progress updates (FR-012)
            timeout_seconds: Action timeout in seconds (default 20s per FR-020)

        Returns:
            ExecutionResult with success status and data

        Raises:
            ExecutionError: If browser action fails
            TimeoutError: If action exceeds timeout (FR-020)
            CancelledError: If user cancels execution (FR-013)

        Example:
            >>> executor = CommandExecutor(browser_service, context_service)
            >>> result = await executor.execute(parsed_command, browser_context)
            >>> assert result.success is True
        """
        start_time = time.time()
        actions_executed = []
        errors = []

        logger.info(f"Executing command: {parsed_command.original_input} (session: {browser_context.session_id})")

        # Handle empty actions
        if not parsed_command.actions:
            logger.warning(f"No actions to execute for command: {parsed_command.original_input}")
            return ExecutionResult(
                success=False,
                message="No actions to execute. Command may be unclear or incomplete.",
                actions_executed=[],
                extracted_data=None,
                duration_ms=int((time.time() - start_time) * 1000),
                errors=[]
            )

        # Get browser page
        try:
            page = await self.browser_service.get_page(browser_context.context_id)
        except Exception as e:
            logger.error(f"Failed to get browser page: {e}")
            return ExecutionResult(
                success=False,
                message=f"Browser error: {str(e)}",
                actions_executed=[],
                extracted_data=None,
                duration_ms=int((time.time() - start_time) * 1000),
                errors=[ExecutionError(str(e))]
            )

        # Execute actions sequentially
        total_steps = len(parsed_command.actions)
        extracted_data = None

        for step_number, action in enumerate(parsed_command.actions, start=1):
            # Emit progress update if callback provided (FR-012)
            if progress_callback and total_steps > 1:
                progress_update = ProgressUpdate(
                    step_number=step_number,
                    total_steps=total_steps,
                    message=self._format_progress_message(step_number, total_steps, action),
                    action=action
                )
                progress_callback(progress_update)

            # Execute the action
            try:
                action_result = await self._execute_action(
                    action=action,
                    page=page,
                    session_id=browser_context.session_id,
                    context_service=self.context_service,
                    timeout_seconds=timeout_seconds
                )

                # Check if action succeeded
                if action_result.get("status") == "success":
                    actions_executed.append(action)
                    # Store extracted data if present
                    if "extracted_data" in action_result.get("result_data", {}):
                        extracted_data = action_result["result_data"]["extracted_data"]
                else:
                    # Action failed - stop execution and report error
                    error_msg = action_result.get("error_message", "Unknown error")
                    logger.error(f"Action failed at step {step_number}/{total_steps}: {error_msg}")

                    error = ExecutionError(
                        message=error_msg,
                        retry_suggestion=self._suggest_retry(action, error_msg),
                        failed_action=action
                    )
                    errors.append(error)

                    # Stop multi-step execution on first failure
                    duration_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=False,
                        message=self._format_error_message(step_number, total_steps, action, error_msg),
                        actions_executed=actions_executed,
                        extracted_data=None,
                        duration_ms=duration_ms,
                        errors=errors
                    )

            except TimeoutError as e:
                logger.error(f"Timeout at step {step_number}/{total_steps}: {e}")
                error = ExecutionError(
                    message=f"Action timeout after {timeout_seconds}s: {str(e)}",
                    retry_suggestion=f"Try increasing timeout with /timeout {timeout_seconds * 2}",
                    failed_action=action
                )
                errors.append(error)

                duration_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    success=False,
                    message=self._format_error_message(step_number, total_steps, action, str(e)),
                    actions_executed=actions_executed,
                    extracted_data=None,
                    duration_ms=duration_ms,
                    errors=errors
                )

            except Exception as e:
                logger.error(f"Unexpected error at step {step_number}/{total_steps}: {e}")
                error = ExecutionError(
                    message=str(e),
                    retry_suggestion="Try rephrasing your command or breaking it into smaller steps",
                    failed_action=action
                )
                errors.append(error)

                duration_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    success=False,
                    message=self._format_error_message(step_number, total_steps, action, str(e)),
                    actions_executed=actions_executed,
                    extracted_data=None,
                    duration_ms=duration_ms,
                    errors=errors
                )

        # All actions succeeded
        duration_ms = int((time.time() - start_time) * 1000)
        success_message = self._format_success_message(parsed_command, actions_executed, extracted_data)

        logger.info(f"Command execution successful: {success_message}")

        return ExecutionResult(
            success=True,
            message=success_message,
            actions_executed=actions_executed,
            extracted_data=extracted_data,
            duration_ms=duration_ms,
            errors=[]
        )

    async def _execute_action(
        self,
        action: BrowserAction,
        page: Any,
        session_id: str,
        context_service: ContextService,
        timeout_seconds: int
    ) -> dict:
        """Execute a single browser action.

        Args:
            action: Browser action to execute
            page: Playwright page instance
            session_id: Current session ID
            context_service: Context service for state updates
            timeout_seconds: Action timeout

        Returns:
            ActionResult dictionary from action handler

        Raises:
            Exception: If action execution fails
        """
        from browser_agent.browser import actions

        if isinstance(action, NavigateAction):
            return await actions.execute_navigate(
                action=action,
                page=page,
                session_id=session_id,
                context_service=context_service,
                timeout_seconds=timeout_seconds
            )
        elif isinstance(action, ClickAction):
            # Try to use click with element finder if available
            try:
                from browser_agent.browser.element_finder import ElementFinder
                element_finder = ElementFinder(page)
                return await actions.execute_click_with_finder(
                    action=action,
                    page=page,
                    session_id=session_id,
                    context_service=context_service,
                    element_finder=element_finder,
                    timeout_seconds=timeout_seconds
                )
            except (ImportError, AttributeError):
                # Fallback to basic click
                return await actions.execute_click(
                    action=action,
                    page=page,
                    session_id=session_id,
                    context_service=context_service,
                    timeout_seconds=timeout_seconds
                )
        elif isinstance(action, TypeAction):
            # Try to use type with element finder if available
            try:
                from browser_agent.browser.element_finder import ElementFinder
                element_finder = ElementFinder(page)
                return await actions.execute_type_with_finder(
                    action=action,
                    page=page,
                    session_id=session_id,
                    context_service=context_service,
                    element_finder=element_finder,
                    timeout_seconds=timeout_seconds
                )
            except (ImportError, AttributeError):
                # Fallback to basic type
                return await actions.execute_type(
                    action=action,
                    page=page,
                    session_id=session_id,
                    context_service=context_service,
                    timeout_seconds=timeout_seconds
                )
        elif isinstance(action, ExtractAction):
            # TODO: Implement extraction in US2-001
            logger.warning(f"Extract action not yet implemented: {action}")
            return {
                "action_type": "extract",
                "status": "error",
                "result_data": {},
                "error_message": "Extraction actions not yet implemented (see US2-001)"
            }
        elif isinstance(action, ScrollAction):
            # TODO: Implement scroll action
            logger.warning(f"Scroll action not yet implemented: {action}")
            return {
                "action_type": "scroll",
                "status": "error",
                "result_data": {},
                "error_message": "Scroll actions not yet implemented"
            }
        elif isinstance(action, ConfigureAction):
            # TODO: Implement configuration actions (timeout, etc.)
            logger.warning(f"Configure action not yet implemented: {action}")
            return {
                "action_type": "configure",
                "status": "error",
                "result_data": {},
                "error_message": "Configuration actions not yet implemented (see POLISH-001)"
            }
        else:
            raise ValueError(f"Unknown action type: {type(action)}")

    def _format_progress_message(self, step: int, total: int, action: BrowserAction) -> str:
        """Format progress update message for multi-step execution.

        Args:
            step: Current step number (1-indexed)
            total: Total number of steps
            action: Action being executed

        Returns:
            Human-readable progress message
        """
        action_desc = self._describe_action(action)
        return f"Step {step} of {total}: {action_desc}..."

    def _format_success_message(
        self,
        parsed_command: ParsedCommand,
        actions_executed: List[BrowserAction],
        extracted_data: Optional[Any]
    ) -> str:
        """Format success message per FR-008.

        Args:
            parsed_command: Original parsed command
            actions_executed: Actions that were executed
            extracted_data: Any data extracted

        Returns:
            Human-readable success message
        """
        if len(actions_executed) == 0:
            return "No actions executed"

        if len(actions_executed) == 1:
            action = actions_executed[0]
            if isinstance(action, NavigateAction):
                return f"Successfully navigated to {action.url}"
            elif isinstance(action, ClickAction):
                return f"Clicked '{action.element_description}'"
            elif isinstance(action, TypeAction):
                return f"Typed '{action.text}' into {action.element_description}"
            else:
                return f"Successfully executed {type(action).__name__}"
        else:
            # Multi-step success
            return f"Successfully completed {len(actions_executed)} actions"

    def _format_error_message(
        self,
        step: int,
        total: int,
        action: BrowserAction,
        error: str
    ) -> str:
        """Format error message per FR-009.

        Args:
            step: Failed step number
            total: Total steps
            action: Action that failed
            error: Error description

        Returns:
            Human-readable error message
        """
        action_desc = self._describe_action(action)

        if total == 1:
            return f"Failed to {action_desc}: {error}"
        else:
            return f"Failed at step {step} of {total} ({action_desc}): {error}"

    def _describe_action(self, action: BrowserAction) -> str:
        """Get human-readable description of action.

        Args:
            action: Browser action

        Returns:
            Short description string
        """
        if isinstance(action, NavigateAction):
            return f"navigate to {action.url}"
        elif isinstance(action, ClickAction):
            return f"click '{action.element_description}'"
        elif isinstance(action, TypeAction):
            return f"type '{action.text}' into {action.element_description}"
        elif isinstance(action, ExtractAction):
            return f"extract {action.target_description}"
        elif isinstance(action, ScrollAction):
            return f"scroll {action.direction}"
        elif isinstance(action, ConfigureAction):
            return f"configure {action.setting}"
        else:
            return str(action)

    def _suggest_retry(self, action: BrowserAction, error: str) -> str:
        """Generate retry suggestion per FR-009a.

        Args:
            action: Action that failed
            error: Error message

        Returns:
            Actionable retry suggestion
        """
        error_lower = error.lower()

        # Timeout errors
        if "timeout" in error_lower:
            return "Try increasing timeout with /timeout 60 or wait a few seconds and try again"

        # Element not found
        if "not found" in error_lower or "element" in error_lower:
            return "Wait a few seconds, or ask me to list all elements first, or be more specific about which element"

        # Network errors
        if "network" in error_lower or "connection" in error_lower:
            return "Check your internet connection and try again"

        # Generic suggestion
        return "Try rephrasing your command or breaking it into smaller steps"
