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
    execute_click_with_finder,
    execute_type,
    execute_type_with_finder,
    create_action_result,
)
from browser_agent.browser.element_finder import (
    ElementFinder,
    FindStrategy,
)

__all__ = [
    "BrowserContext",
    "PageState",
    "ContextService",
    "ContextNotFoundError",
    "ContextAlreadyExistsError",
    "execute_navigate",
    "execute_click",
    "execute_click_with_finder",
    "execute_type",
    "execute_type_with_finder",
    "create_action_result",
    "ElementFinder",
    "FindStrategy",
]
