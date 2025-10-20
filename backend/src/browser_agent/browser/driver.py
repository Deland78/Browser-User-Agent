"""Browser driver abstraction layer using Playwright."""

import logging
from typing import Protocol, Optional
from uuid import uuid4

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Error as PlaywrightError,
)

from browser_agent.config import settings

logger = logging.getLogger(__name__)


# Protocol definitions for type safety
class BrowserService(Protocol):
    """Protocol defining the browser automation service interface."""

    async def create_context(
        self,
        session_id: str,
        headless: Optional[bool] = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> str:
        """
        Create a new browser context.

        Args:
            session_id: Associated chat session ID
            headless: Run in headless mode (None = use settings default)
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height

        Returns:
            context_id: Unique identifier for the created context

        Raises:
            BrowserError: If context creation fails
        """
        ...

    async def get_page(self, context_id: str) -> Page:
        """
        Get the active page for a context.

        Args:
            context_id: Browser context identifier

        Returns:
            Page object for the context

        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        ...

    async def close_context(self, context_id: str) -> None:
        """
        Close a browser context and cleanup resources.

        Args:
            context_id: Browser context identifier

        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        ...


class ContextNotFoundError(Exception):
    """Raised when attempting to access a non-existent browser context."""

    pass


class BrowserError(Exception):
    """Raised when browser operations fail."""

    pass


class PlaywrightBrowserService:
    """
    Playwright-based implementation of the BrowserService protocol.

    Manages browser lifecycle, context creation, and page management.
    Supports headless/headful mode configuration.
    """

    def __init__(self) -> None:
        """Initialize the browser service."""
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: dict[str, BrowserContext] = {}
        self._session_to_context: dict[str, str] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize Playwright and launch browser.

        Should be called before any other operations.
        """
        if self._initialized:
            logger.warning("Browser service already initialized")
            return

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.browser_headless
            )
            self._initialized = True
            logger.info(
                f"Browser launched successfully (headless={settings.browser_headless})"
            )
        except PlaywrightError as e:
            raise BrowserError(f"Failed to initialize browser: {e}") from e

    async def shutdown(self) -> None:
        """
        Shutdown browser and cleanup all resources.

        Closes all contexts and browser instance.
        """
        if not self._initialized:
            return

        try:
            # Close all contexts
            for context_id in list(self._contexts.keys()):
                await self.close_context(context_id)

            # Close browser
            if self._browser:
                await self._browser.close()
                self._browser = None

            # Stop playwright
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._initialized = False
            logger.info("Browser service shut down successfully")
        except PlaywrightError as e:
            logger.error(f"Error during browser shutdown: {e}")
            raise BrowserError(f"Failed to shutdown browser: {e}") from e

    async def create_context(
        self,
        session_id: str,
        headless: Optional[bool] = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> str:
        """
        Create a new browser context for a chat session.

        Args:
            session_id: Associated chat session ID
            headless: Run in headless mode (None = use settings default)
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height

        Returns:
            context_id: Unique identifier for the created context

        Raises:
            BrowserError: If context creation fails
        """
        if not self._initialized or not self._browser:
            raise BrowserError("Browser service not initialized. Call initialize() first.")

        # Check if session already has a context
        if session_id in self._session_to_context:
            existing_context_id = self._session_to_context[session_id]
            logger.warning(
                f"Session {session_id} already has context {existing_context_id}"
            )
            return existing_context_id

        try:
            context_id = str(uuid4())

            # Create new browser context
            context = await self._browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
            )

            # Create initial page
            page = await context.new_page()

            # Store context
            self._contexts[context_id] = context
            self._session_to_context[session_id] = context_id

            logger.info(
                f"Created browser context {context_id} for session {session_id}"
            )
            return context_id

        except PlaywrightError as e:
            raise BrowserError(f"Failed to create browser context: {e}") from e

    async def get_page(self, context_id: str) -> Page:
        """
        Get the active page for a browser context.

        Args:
            context_id: Browser context identifier

        Returns:
            Page object for the context

        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        context = self._contexts.get(context_id)
        if not context:
            raise ContextNotFoundError(f"Context {context_id} not found")

        pages = context.pages
        if not pages:
            # Create a new page if none exists
            try:
                page = await context.new_page()
                logger.info(f"Created new page for context {context_id}")
                return page
            except PlaywrightError as e:
                raise BrowserError(f"Failed to create page: {e}") from e

        # Return the first (main) page
        return pages[0]

    async def close_context(self, context_id: str) -> None:
        """
        Close a browser context and cleanup resources.

        Args:
            context_id: Browser context identifier

        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        context = self._contexts.get(context_id)
        if not context:
            raise ContextNotFoundError(f"Context {context_id} not found")

        try:
            await context.close()

            # Cleanup tracking dictionaries
            del self._contexts[context_id]

            # Remove session mapping
            session_id = next(
                (sid for sid, cid in self._session_to_context.items() if cid == context_id),
                None
            )
            if session_id:
                del self._session_to_context[session_id]

            logger.info(f"Closed browser context {context_id}")

        except PlaywrightError as e:
            raise BrowserError(f"Failed to close context: {e}") from e

    def get_context_for_session(self, session_id: str) -> Optional[str]:
        """
        Get the context ID associated with a session.

        Args:
            session_id: Chat session ID

        Returns:
            context_id if found, None otherwise
        """
        return self._session_to_context.get(session_id)

    @property
    def is_initialized(self) -> bool:
        """Check if browser service is initialized."""
        return self._initialized
