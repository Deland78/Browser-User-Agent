"""Browser automation adapters."""

from browser_agent.browser.context import (
    BrowserContext,
    PageState,
    ContextService,
    ContextNotFoundError,
    ContextAlreadyExistsError,
)
from browser_agent.browser.actions import (
    execute_navigate,
    execute_click,
    execute_type,
    create_action_result,
)

__all__ = [
    "BrowserContext",
    "PageState",
    "ContextService",
    "ContextNotFoundError",
    "ContextAlreadyExistsError",
    "execute_navigate",
    "execute_click",
    "execute_type",
    "create_action_result",
]
