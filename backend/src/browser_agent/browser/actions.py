"""Browser action execution handlers.

This module implements handlers for executing structured browser actions
(NavigateAction, ClickAction, TypeAction, etc.) using Playwright.

Per tasks.md US1-003, US1-004, US1-005:
- NavigateAction handler with timeout support
- ClickAction handler with element finding
- TypeAction handler with element finding

Per data-model.md Entity 5 (ActionResult):
- Returns structured results with action_type, status, result_data, error_message
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging

from browser_agent.agent.command_parser import (
    NavigateAction,
    ClickAction,
    TypeAction,
    ExtractAction,
    ScrollAction,
    ConfigureAction,
)
from browser_agent.browser.context import PageState, ContextService

logger = logging.getLogger(__name__)


# ============================================================================
# Action Result Structure
# Per data-model.md Entity 5
# ============================================================================


def create_action_result(
    action_type: str,
    status: str,
    result_data: Dict[str, Any],
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Create standardized ActionResult structure.

    Args:
        action_type: Type of action (navigate, click, type, etc.)
        status: Result status (success, error, partial)
        result_data: Action-specific result data
        error_message: Error description if status is error

    Returns:
        ActionResult dictionary per data-model.md Entity 5
    """
    return {
        "action_type": action_type,
        "status": status,
        "result_data": result_data,
        "error_message": error_message,
    }


# ============================================================================
# Navigate Action Handler
# Per tasks.md US1-003
# ============================================================================


async def execute_navigate(
    action: NavigateAction,
    page: Any,  # Playwright Page
    session_id: str,
    context_service: ContextService,
    timeout_seconds: int = 20,  # Default from FR-020
) -> Dict[str, Any]:
    """Execute navigation action using Playwright.

    Args:
        action: NavigateAction with URL and wait_for option
        page: Playwright page instance
        session_id: Current session ID
        context_service: Service for updating BrowserContext
        timeout_seconds: Navigation timeout in seconds (default 20s per FR-020)

    Returns:
        ActionResult dictionary

    Per FR-020:
    - Default timeout is 20 seconds
    - Timeout is configurable via session settings
    - On timeout: abort action, report error with duration, provide retry suggestions
    """
    logger.info(f"Executing navigate action: {action.url} (session: {session_id})")

    # Update context to LOADING state
    try:
        await context_service.update_context(
            session_id=session_id,
            page_state=PageState.LOADING,
        )
    except Exception as e:
        logger.warning(f"Failed to update context to LOADING: {e}")

    # Convert wait_for to Playwright's wait_until parameter
    wait_until = action.wait_for  # load, domcontentloaded, networkidle

    # Convert timeout to milliseconds
    timeout_ms = timeout_seconds * 1000

    try:
        # Execute navigation
        await page.goto(
            action.url,
            wait_until=wait_until,
            timeout=timeout_ms,
        )

        # Get final URL (may differ due to redirects)
        final_url = page.url

        # Get page title
        page_title = await page.title()

        # Update context to READY state
        await context_service.update_context(
            session_id=session_id,
            current_url=final_url,
            page_title=page_title,
            page_state=PageState.READY,
        )

        logger.info(f"Navigation successful: {final_url}")

        return create_action_result(
            action_type="navigate",
            status="success",
            result_data={
                "url": action.url,
                "final_url": final_url,
                "page_title": page_title,
                "wait_for": wait_until,
            },
            error_message=None,
        )

    except Exception as e:
        # Handle navigation errors
        error_type = type(e).__name__
        error_message = str(e)

        logger.error(f"Navigation failed: {error_type} - {error_message}")

        # Update context to ERROR state
        try:
            await context_service.update_context(
                session_id=session_id,
                page_state=PageState.ERROR,
            )
        except Exception as ctx_error:
            logger.warning(f"Failed to update context to ERROR: {ctx_error}")

        # Check if it's a timeout error
        if "timeout" in error_type.lower() or "timeout" in error_message.lower():
            error_message = f"Navigation timeout after {timeout_seconds}s: {error_message}"
            logger.info("Retry suggestion: Increase timeout or check network connectivity")

        return create_action_result(
            action_type="navigate",
            status="error",
            result_data={
                "url": action.url,
                "error_type": error_type,
            },
            error_message=error_message,
        )


# ============================================================================
# Click Action Handler
# Per tasks.md US1-004
# ============================================================================


async def execute_click(
    action: ClickAction,
    page: Any,  # Playwright Page
    session_id: str,
    context_service: ContextService,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    """Execute click action using Playwright.

    Args:
        action: ClickAction with element description and optional selector
        page: Playwright page instance
        session_id: Current session ID
        context_service: Service for updating BrowserContext
        timeout_seconds: Action timeout in seconds

    Returns:
        ActionResult dictionary

    Note: Full implementation requires element finder from US1-006.
    This is a minimal implementation for US1-004.
    """
    logger.info(f"Executing click action: {action.element_description} (session: {session_id})")

    # TODO: Integrate with element finder from US1-006
    # For now, use simple selector if provided

    timeout_ms = timeout_seconds * 1000

    try:
        # If selector provided, use it directly
        if action.selector:
            await page.click(action.selector, timeout=timeout_ms)
            element_found = action.selector
        else:
            # Fallback: try to find by text
            if action.text:
                await page.click(f"text={action.text}", timeout=timeout_ms)
                element_found = f"text={action.text}"
            else:
                raise ValueError("No selector or text provided for click action")

        logger.info(f"Click successful: {element_found}")

        return create_action_result(
            action_type="click",
            status="success",
            result_data={
                "element_description": action.element_description,
                "element_found": element_found,
            },
            error_message=None,
        )

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)

        logger.error(f"Click failed: {error_type} - {error_message}")

        if "timeout" in error_type.lower() or "timeout" in error_message.lower():
            error_message = f"Click timeout after {timeout_seconds}s: Element not found or not clickable"

        return create_action_result(
            action_type="click",
            status="error",
            result_data={
                "element_description": action.element_description,
                "error_type": error_type,
            },
            error_message=error_message,
        )


async def execute_click_with_finder(
    action: ClickAction,
    page: Any,  # Playwright Page
    session_id: str,
    context_service: ContextService,
    element_finder: Any,  # ElementFinder instance
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    """Execute click action using ElementFinder for element location.

    Args:
        action: ClickAction with element description and search criteria
        page: Playwright page instance
        session_id: Current session ID
        context_service: Service for updating BrowserContext
        element_finder: ElementFinder instance for multi-strategy element location
        timeout_seconds: Action timeout in seconds

    Returns:
        ActionResult dictionary

    Per US1-004: Integrates ElementFinder from US1-006 for robust element location.
    """
    from browser_agent.browser.element_finder import FindStrategy

    logger.info(f"Executing click with finder: {action.element_description} (session: {session_id})")

    timeout_ms = timeout_seconds * 1000

    try:
        # Use ElementFinder to locate elements
        strategy = FindStrategy.SELECTOR if action.selector else FindStrategy.COMBINED

        if action.selector:
            elements = await element_finder.find_elements(
                strategy=strategy,
                value=action.selector
            )
        elif action.text:
            elements = await element_finder.find_elements(
                strategy=FindStrategy.TEXT,
                value=action.text,
                exact=True
            )
        else:
            raise ValueError("ClickAction must specify either selector or text")

        if not elements:
            error_msg = f"Element not found: {action.element_description}"
            logger.warning(error_msg)
            return create_action_result(
                action_type="click",
                status="error",
                result_data={"element_description": action.element_description},
                error_message=error_msg
            )

        # Click first matching element
        if action.selector:
            locator = page.locator(action.selector)
        elif action.text:
            locator = page.get_by_text(action.text, exact=True)

        await locator.click(timeout=timeout_ms)

        logger.info(f"Click successful: {action.element_description}")

        return create_action_result(
            action_type="click",
            status="success",
            result_data={
                "element_description": action.element_description,
                "elements_found": len(elements),
                "clicked_element": elements[0]
            },
            error_message=None
        )

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(f"Click failed: {error_type} - {error_message}")

        if "timeout" in error_type.lower() or "timeout" in error_message.lower():
            error_message = f"Click timeout after {timeout_seconds}s: {error_message}"

        return create_action_result(
            action_type="click",
            status="error",
            result_data={"element_description": action.element_description, "error_type": error_type},
            error_message=error_message
        )


# ============================================================================
# Type Action Handler
# Per tasks.md US1-005
# ============================================================================


async def execute_type(
    action: TypeAction,
    page: Any,  # Playwright Page
    session_id: str,
    context_service: ContextService,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    """Execute type action using Playwright.

    Args:
        action: TypeAction with element description, text, and options
        page: Playwright page instance
        session_id: Current session ID
        context_service: Service for updating BrowserContext
        timeout_seconds: Action timeout in seconds

    Returns:
        ActionResult dictionary

    Note: Full implementation requires element finder from US1-006.
    This is a minimal implementation for US1-005.
    """
    logger.info(f"Executing type action: '{action.text}' into {action.element_description} (session: {session_id})")

    timeout_ms = timeout_seconds * 1000

    try:
        # If selector provided, use it directly
        if action.selector:
            element_found = action.selector
        else:
            # Fallback: try to find by description as placeholder
            element_found = f"[placeholder*='{action.element_description}' i]"

        # Clear field first if requested
        if action.clear_first:
            await page.fill(element_found, "", timeout=timeout_ms)

        # Type the text
        await page.fill(element_found, action.text, timeout=timeout_ms)

        # Press Enter if requested
        if action.press_enter:
            await page.press(element_found, "Enter", timeout=timeout_ms)

        logger.info(f"Type successful: {element_found}")

        return create_action_result(
            action_type="type",
            status="success",
            result_data={
                "element_description": action.element_description,
                "element_found": element_found,
                "text": action.text,
                "press_enter": action.press_enter,
            },
            error_message=None,
        )

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)

        logger.error(f"Type failed: {error_type} - {error_message}")

        if "timeout" in error_type.lower() or "timeout" in error_message.lower():
            error_message = f"Type timeout after {timeout_seconds}s: Element not found or not editable"

        return create_action_result(
            action_type="type",
            status="error",
            result_data={
                "element_description": action.element_description,
                "text": action.text,
                "error_type": error_type,
            },
            error_message=error_message,
        )


async def execute_type_with_finder(
    action: TypeAction,
    page: Any,  # Playwright Page
    session_id: str,
    context_service: ContextService,
    element_finder: Any,  # ElementFinder instance
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    """Execute type action using ElementFinder for element location.

    Args:
        action: TypeAction with element description, text, and options
        page: Playwright page instance
        session_id: Current session ID
        context_service: Service for updating BrowserContext
        element_finder: ElementFinder instance for multi-strategy element location
        timeout_seconds: Action timeout in seconds

    Returns:
        ActionResult dictionary

    Per US1-005: Integrates ElementFinder from US1-006 for robust element location.
    Supports clear_first and press_enter options per browser-api.yaml.
    """
    from browser_agent.browser.element_finder import FindStrategy

    logger.info(f"Executing type with finder: '{action.text}' into {action.element_description} (session: {session_id})")

    timeout_ms = timeout_seconds * 1000

    try:
        # Use ElementFinder to locate elements
        strategy = FindStrategy.SELECTOR if action.selector else FindStrategy.COMBINED

        if action.selector:
            elements = await element_finder.find_elements(
                strategy=strategy,
                value=action.selector
            )
        else:
            # Try to find input by element description (text/label)
            elements = await element_finder.find_elements(
                strategy=FindStrategy.LABEL,
                value=action.element_description
            )

        if not elements:
            error_msg = f"Element not found: {action.element_description}"
            logger.warning(error_msg)
            return create_action_result(
                action_type="type",
                status="error",
                result_data={"element_description": action.element_description},
                error_message=error_msg
            )

        # Get locator for the element
        if action.selector:
            locator = page.locator(action.selector)
        else:
            # Use first element found
            locator = page.locator(action.element_description)

        # Type text based on clear_first option
        if action.clear_first:
            # fill() clears the field first, then types
            await locator.fill(action.text, timeout=timeout_ms)
        else:
            # type() appends to existing text
            await locator.type(action.text, timeout=timeout_ms)

        # Press Enter if requested
        if action.press_enter:
            await locator.press("Enter", timeout=timeout_ms)

        logger.info(f"Type successful: {action.element_description}")

        return create_action_result(
            action_type="type",
            status="success",
            result_data={
                "element_description": action.element_description,
                "elements_found": len(elements),
                "text": action.text,
                "clear_first": action.clear_first,
                "press_enter": action.press_enter,
            },
            error_message=None
        )

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(f"Type failed: {error_type} - {error_message}")

        if "timeout" in error_type.lower() or "timeout" in error_message.lower():
            error_message = f"Type timeout after {timeout_seconds}s: {error_message}"

        return create_action_result(
            action_type="type",
            status="error",
            result_data={
                "element_description": action.element_description,
                "text": action.text,
                "error_type": error_type
            },
            error_message=error_message
        )
