"""BrowserContext state management.

Implements:
- BrowserContext model per data-model.md Entity 4
- ContextService for CRUD operations with async SQLite
- Page state tracking and get_page_state() method

Per tasks.md INFRA-007:
- Track current_url, page_title, page_state
- Implement get_page_state() method per browser-api.yaml
- Link context to session (one-to-one relationship)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from browser_agent.db.init import get_session
from browser_agent.db import models as db_models


class PageState(str, Enum):
    """Page state values per data-model.md."""

    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ContextNotFoundError(Exception):
    """Raised when a browser context is not found."""

    pass


class ContextAlreadyExistsError(Exception):
    """Raised when attempting to create duplicate context for session."""

    pass


@dataclass
class BrowserContext:
    """Represents the state of the browser instance being controlled.

    Per data-model.md Entity 4 (BrowserContext):
    - context_id: Unique identifier
    - session_id: Parent session
    - current_url: Currently loaded page URL
    - page_title: Title of current page
    - page_state: loading, ready, error, idle
    - last_page_change_at: Last browser action timestamp

    Validation Rules:
    - current_url must be valid URL or empty string (for new context)
    - Single active context per session (enforced at application level)

    Notes:
    - Persistent within session (per research.md)
    - Cleaned up when session ends
    """

    context_id: str
    session_id: str
    page_state: PageState = PageState.IDLE
    current_url: Optional[str] = None
    page_title: Optional[str] = None
    last_page_change_at: Optional[datetime] = None


class ContextService:
    """Async SQLite storage for browser contexts.

    Per tasks.md INFRA-007:
    - Create, get, update, delete operations
    - Track page state and navigation
    - One-to-one relationship with sessions
    - Implement get_page_state() per browser-api.yaml

    Thread-safety: Async-safe via SQLAlchemy async sessions
    Persistence: SQLite database (ephemeral per spec)
    """

    async def create_context(
        self,
        session_id: str,
        current_url: Optional[str] = None,
        page_title: Optional[str] = None,
        page_state: PageState = PageState.IDLE,
    ) -> BrowserContext:
        """Create a new browser context for a session.

        Args:
            session_id: Parent session ID
            current_url: Optional initial URL
            page_title: Optional initial page title
            page_state: Initial page state (default: IDLE)

        Returns:
            BrowserContext: Newly created context

        Raises:
            ContextAlreadyExistsError: If context already exists for session

        Example:
            >>> service = ContextService()
            >>> context = await service.create_context(session_id="session-123")
        """
        context_id = str(uuid4())
        context = BrowserContext(
            context_id=context_id,
            session_id=session_id,
            current_url=current_url,
            page_title=page_title,
            page_state=page_state,
        )

        # Convert to DB model
        db_context = db_models.BrowserContext(
            context_id=context.context_id,
            session_id=context.session_id,
            current_url=context.current_url,
            page_title=context.page_title,
            page_state=db_models.PageState(context.page_state.value),
            last_page_change_at=context.last_page_change_at,
        )

        # Save to database
        try:
            async with get_session() as session:
                session.add(db_context)
                await session.commit()
                await session.refresh(db_context)
        except IntegrityError:
            raise ContextAlreadyExistsError(
                f"Context already exists for session: {session_id}"
            )

        return context

    async def get_context_by_session(self, session_id: str) -> BrowserContext:
        """Retrieve context by session ID.

        Args:
            session_id: Session identifier

        Returns:
            BrowserContext: Retrieved context

        Raises:
            ContextNotFoundError: If context doesn't exist

        Example:
            >>> context = await service.get_context_by_session("session-123")
        """
        async with get_session() as session:
            result = await session.execute(
                select(db_models.BrowserContext).where(
                    db_models.BrowserContext.session_id == session_id
                )
            )
            db_context = result.scalar_one_or_none()

            if db_context is None:
                raise ContextNotFoundError(f"Context not found for session: {session_id}")

            return self._db_to_dataclass(db_context)

    async def update_context(
        self,
        session_id: str,
        current_url: Optional[str] = None,
        page_title: Optional[str] = None,
        page_state: Optional[PageState] = None,
    ) -> BrowserContext:
        """Update browser context state.

        Args:
            session_id: Session identifier
            current_url: New URL (optional)
            page_title: New page title (optional)
            page_state: New page state (optional)

        Returns:
            BrowserContext: Updated context

        Raises:
            ContextNotFoundError: If context doesn't exist

        Example:
            >>> updated = await service.update_context(
            ...     session_id="session-123",
            ...     current_url="https://google.com",
            ...     page_state=PageState.READY
            ... )
        """
        async with get_session() as session:
            result = await session.execute(
                select(db_models.BrowserContext).where(
                    db_models.BrowserContext.session_id == session_id
                )
            )
            db_context = result.scalar_one_or_none()

            if db_context is None:
                raise ContextNotFoundError(f"Context not found for session: {session_id}")

            # Track if any page-related field changed
            page_changed = False

            # Update fields if provided
            if current_url is not None:
                db_context.current_url = current_url
                page_changed = True

            if page_title is not None:
                db_context.page_title = page_title
                page_changed = True

            if page_state is not None:
                db_context.page_state = db_models.PageState(page_state.value)
                # Page state changes (especially LOADING->READY) indicate page change
                page_changed = True

            # Update timestamp if page changed
            if page_changed:
                db_context.last_page_change_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(db_context)

            return self._db_to_dataclass(db_context)

    async def get_page_state(self, session_id: str) -> dict[str, Any]:
        """Get current page state per browser-api.yaml.

        Args:
            session_id: Session identifier

        Returns:
            dict: Page state with keys:
                - current_url: str | None
                - page_title: str | None
                - page_state: str (enum value)
                - last_page_change_at: datetime | None

        Raises:
            ContextNotFoundError: If context doesn't exist

        Example:
            >>> state = await service.get_page_state("session-123")
            >>> print(state["current_url"])
            https://example.com
        """
        context = await self.get_context_by_session(session_id)

        return {
            "current_url": context.current_url,
            "page_title": context.page_title,
            "page_state": context.page_state.value,
            "last_page_change_at": context.last_page_change_at,
        }

    async def delete_context(self, session_id: str) -> None:
        """Delete browser context.

        Args:
            session_id: Session identifier

        Raises:
            ContextNotFoundError: If context doesn't exist

        Example:
            >>> await service.delete_context("session-123")
        """
        async with get_session() as session:
            result = await session.execute(
                select(db_models.BrowserContext).where(
                    db_models.BrowserContext.session_id == session_id
                )
            )
            db_context = result.scalar_one_or_none()

            if db_context is None:
                raise ContextNotFoundError(f"Context not found for session: {session_id}")

            await session.delete(db_context)
            await session.commit()

    def _db_to_dataclass(self, db_context: db_models.BrowserContext) -> BrowserContext:
        """Convert database model to dataclass."""
        return BrowserContext(
            context_id=db_context.context_id,
            session_id=db_context.session_id,
            current_url=db_context.current_url,
            page_title=db_context.page_title,
            page_state=PageState(db_context.page_state.value),
            last_page_change_at=db_context.last_page_change_at,
        )
